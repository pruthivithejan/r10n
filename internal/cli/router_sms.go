package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/charmbracelet/huh"
	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/tui"
)

type smsMessage struct {
	ID     string `json:"id"`
	Number string `json:"number"`
	Date   string `json:"date"`
	Text   string `json:"text"`
}
type smsResponse struct {
	Configured bool         `json:"configured"`
	Saved      bool         `json:"saved"`
	Success    bool         `json:"success"`
	Messages   []smsMessage `json:"messages"`
}

func smsRequest(ctx context.Context, request map[string]any) (smsResponse, error) {
	var result smsResponse
	engine, err := backend.Resolve()
	if err != nil {
		return result, err
	}
	raw, err := json.Marshal(request)
	if err != nil {
		return result, err
	}
	command := engine.Command(ctx, "router-sms")
	command.Stdin = bytes.NewReader(raw)
	var output, diagnostic bytes.Buffer
	command.Stdout, command.Stderr = &output, &diagnostic
	if err = command.Run(); err != nil {
		if ctx.Err() != nil {
			return result, ctx.Err()
		}
		message := strings.TrimSpace(diagnostic.String())
		if message == "" {
			message = err.Error()
		}
		return result, fmt.Errorf("router SMS: %s", tui.SafeText(message))
	}
	if err := json.Unmarshal(output.Bytes(), &result); err != nil {
		return result, fmt.Errorf("router SMS returned an invalid response")
	}
	return result, nil
}

func smsForm(ctx context.Context, fields ...huh.Field) error {
	return tui.RunForm(ctx, huh.NewForm(huh.NewGroup(fields...)))
}

func smsSetup(ctx context.Context) error {
	address, username, password := "192.168.1.1", "", ""
	if err := smsForm(ctx,
		huh.NewInput().Title("Router address").Value(&address),
		huh.NewInput().Title("Router username").Value(&username),
		huh.NewInput().Title("Router password").EchoMode(huh.EchoModePassword).Value(&password),
	); err != nil {
		return err
	}
	result, err := smsRequest(ctx, map[string]any{"action": "setup", "url": address, "username": username, "password": password})
	if err != nil {
		return err
	}
	if !result.Saved {
		return fmt.Errorf("router profile was not saved")
	}
	fmt.Fprintln(stderr, "Router setup saved. Password stored in your OS credential service.")
	return nil
}

func runSMS(ctx context.Context, args []string) error {
	if len(args) != 0 {
		return usage(fmt.Errorf("usage: r10n sms"))
	}
	if !tui.Interactive() {
		return usage(fmt.Errorf("router SMS requires an interactive terminal"))
	}
	var err error
	ctx, err = tui.ResolveSettings(ctx)
	if err != nil {
		return err
	}
	status, err := smsRequest(ctx, map[string]any{"action": "status"})
	if err != nil {
		return err
	}
	if !status.Configured {
		if err := smsSetup(ctx); err != nil {
			return err
		}
	}
	for {
		action := ""
		err := smsForm(ctx, huh.NewSelect[string]().Title("Router SMS").Description("ZLT S10 · Choose an action").Options(
			huh.NewOption("Read inbox", "list"), huh.NewOption("Send message", "send"),
			huh.NewOption("Delete messages", "delete"), huh.NewOption("Router setup", "setup"), huh.NewOption("Back", "back"),
		).Value(&action))
		if err != nil {
			return err
		}
		switch action {
		case "back":
			return nil
		case "setup":
			err = smsSetup(ctx)
		case "list":
			err = smsInbox(ctx)
		case "send":
			err = smsSend(ctx)
		case "delete":
			err = smsDelete(ctx)
		}
		if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
			return err
		}
		if err != nil {
			fmt.Fprintln(stderr, tui.SafeText(err.Error()))
		}
	}
}

func smsInbox(ctx context.Context) error {
	page := 0
	for {
		result, err := smsRequest(ctx, map[string]any{"action": "list", "page": page})
		if err != nil {
			return err
		}
		fmt.Fprintf(stdout, "\nInbox · page %d\n", page+1)
		for _, m := range result.Messages {
			fmt.Fprintf(stdout, "\n[%s] %s · %s\n%s\n", tui.SafeText(m.ID), tui.SafeText(m.Date), tui.SafeText(m.Number), tui.SafeText(m.Text))
		}
		if len(result.Messages) == 0 {
			fmt.Fprintln(stdout, "No messages on this page.")
		}
		options := []huh.Option[string]{huh.NewOption("Refresh", "refresh")}
		if len(result.Messages) > 0 {
			options = append(options, huh.NewOption("Reply", "reply"))
		}
		if len(result.Messages) >= 100 {
			options = append(options, huh.NewOption("Next page", "next"))
		}
		if page > 0 {
			options = append(options, huh.NewOption("Previous page", "previous"))
		}
		options = append(options, huh.NewOption("Back", "back"))
		action := ""
		if err := smsForm(ctx, huh.NewSelect[string]().Title("Inbox").Options(options...).Value(&action)); err != nil {
			return err
		}
		switch action {
		case "back":
			return nil
		case "next":
			page++
		case "previous":
			page--
		case "reply":
			choices := make([]huh.Option[string], 0, len(result.Messages))
			for _, message := range result.Messages {
				choices = append(choices, huh.NewOption(tui.SafeText(fmt.Sprintf("[%s] %s · %s", message.ID, message.Number, message.Text)), message.Number))
			}
			number := ""
			if err := smsForm(ctx, huh.NewSelect[string]().Title("Reply to message").Options(choices...).Value(&number)); err != nil {
				return err
			}
			if err := smsCompose(ctx, number); err != nil {
				return err
			}
		}
	}
}

func smsSend(ctx context.Context) error {
	return smsCompose(ctx, "")
}

func smsCompose(ctx context.Context, number string) error {
	message := ""
	if err := smsForm(ctx, huh.NewInput().Title("Phone number").Description("Include country code when needed").Value(&number), huh.NewText().Title("Message").Value(&message)); err != nil {
		return err
	}
	approve := false
	if err := smsForm(ctx, huh.NewConfirm().Title("Send this SMS?").Description("To: "+tui.SafeText(number)+"\n"+tui.SafeText(message)).Value(&approve)); err != nil {
		return err
	}
	if !approve {
		return nil
	}
	result, err := smsRequest(ctx, map[string]any{"action": "send", "number": number, "message": message})
	if err != nil {
		return err
	}
	if !result.Success {
		return fmt.Errorf("router did not confirm the message")
	}
	fmt.Fprintln(stdout, "Message sent.")
	return nil
}

func smsDelete(ctx context.Context) error {
	page := 0
	for {
		result, err := smsRequest(ctx, map[string]any{"action": "list", "page": page})
		if err != nil {
			return err
		}
		options := make([]huh.Option[string], 0, 4)
		if len(result.Messages) > 0 {
			options = append(options, huh.NewOption("Select messages on this page", "select"))
		}
		if len(result.Messages) >= 100 {
			options = append(options, huh.NewOption("Next page", "next"))
		}
		if page > 0 {
			options = append(options, huh.NewOption("Previous page", "previous"))
		}
		options = append(options, huh.NewOption("Back", "back"))
		action := ""
		if err := smsForm(ctx, huh.NewSelect[string]().Title(fmt.Sprintf("Delete messages · page %d", page+1)).Options(options...).Value(&action)); err != nil {
			return err
		}
		switch action {
		case "back":
			return nil
		case "next":
			page++
			continue
		case "previous":
			page--
			continue
		}
		choices := make([]huh.Option[string], 0, len(result.Messages))
		for _, message := range result.Messages {
			label := fmt.Sprintf("[%s] %s · %s — %s", message.ID, message.Date, message.Number, message.Text)
			choices = append(choices, huh.NewOption(tui.SafeText(label), message.ID))
		}
		var selected []string
		if err := smsForm(ctx, huh.NewMultiSelect[string]().Title("Select messages to delete").Description("Space selects; Enter continues.").Options(choices...).Value(&selected)); err != nil {
			return err
		}
		if len(selected) == 0 {
			continue
		}
		approve := false
		if err := smsForm(ctx, huh.NewConfirm().Title(fmt.Sprintf("Permanently delete %d messages?", len(selected))).Description("IDs: "+strings.Join(selected, ", ")).Value(&approve)); err != nil {
			return err
		}
		if !approve {
			continue
		}
		deleted, err := smsRequest(ctx, map[string]any{"action": "delete", "ids": selected})
		if err != nil {
			return err
		}
		if !deleted.Success {
			return fmt.Errorf("router did not confirm deletion")
		}
		fmt.Fprintf(stdout, "Deleted %d messages.\n", len(selected))
		return nil
	}
}
