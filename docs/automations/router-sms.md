---
icon: lucide/message-square
---

# Router SMS

Read, send, reply to, and delete SMS messages using the SIM in a ZLT S10 router.

## Setup

Connect the computer to the router's network and run:

```bash
r10n sms
```

You can also open `r10n` and choose `/sms` from the command launcher. On first use, enter the router's address (for example `192.168.1.1`), web-interface username, and password. The address and username are saved in the per-user configuration directory; the password is saved in the operating system credential service. An available credential service is required. Choose **Router setup** to change these details later.

The current implementation targets the ZLT S10 web interface with firmware `S10_1.16.9`. Other firmware and models may use different authentication or SMS protocols.

## Use

Choose **Read inbox** to display message IDs, dates, senders, and text. Choose **Refresh** to fetch new messages, navigate through inbox pages, or **Reply** to send to a message's sender. Choose **Send message** to compose a new message. Review and confirm its recipient and content before it is sent.

Choose **Delete messages** to navigate pages and select one or more messages with Space. Review the IDs and confirm before deletion. Deleted messages cannot be restored through r10n. The router reports completion separately from accepting a request; if completion times out, check the router before retrying to avoid a duplicate send.

SMS operations require an interactive terminal and connection to the router. They do not accept passwords on the command line. Sending can incur carrier charges; the SIM and network must support SMS. Characters outside the Unicode basic multilingual plane, including many emoji, are not supported by this firmware integration.

## Troubleshooting

- **Login fails:** Confirm the web-interface username and password and update **Router setup**. Check the router web interface for a lockout before retrying.
- **Router cannot be reached:** Confirm its address in **Router setup** and that the computer is connected to its network.
- **Credential service unavailable:** Enable the system keychain or credential service, then repeat setup.
- **Completion unknown:** Check the router's inbox or sent messages before repeating the operation.
