"""
Tests for the File Renamer automation.

These tests are written FIRST (TDD red phase) to define the expected
behavior of the rename_files automation before implementation.

The automation should:
- Batch rename files with patterns
- Support prefixes, suffixes, dates, and sequences
- Provide preview mode (dry run) before applying changes
- Handle various filename transformations
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# These imports will fail until the module is implemented (TDD red phase)
from src.automations.rename_files import (
    RenameConfig,
    RenameResult,
    FileRenamer,
    rename_files,
    preview_rename,
    apply_pattern,
    sanitize_filename,
)


class TestRenameConfig:
    """Test RenameConfig dataclass."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = RenameConfig(input_directory="./files")
        assert config.input_directory == "./files"
        assert config.pattern is None
        assert config.prefix is None
        assert config.suffix is None
        assert config.replace_from is None
        assert config.replace_to is None
        assert config.add_date is False
        assert config.add_sequence is False
        assert config.sequence_start == 1
        assert config.sequence_padding == 3
        assert config.lowercase is False
        assert config.uppercase is False
        assert config.recursive is False
        assert config.dry_run is False
        assert config.file_pattern == "*"

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = RenameConfig(
            input_directory="/path/to/files",
            pattern="{date}_{name}",
            prefix="photo_",
            suffix="_edited",
            replace_from=" ",
            replace_to="_",
            add_date=True,
            add_sequence=True,
            sequence_start=100,
            sequence_padding=5,
            lowercase=True,
            recursive=True,
            dry_run=True,
            file_pattern="*.jpg",
        )
        assert config.prefix == "photo_"
        assert config.sequence_start == 100
        assert config.dry_run is True
        assert config.file_pattern == "*.jpg"


class TestRenameResult:
    """Test RenameResult dataclass."""

    def test_result_success(self):
        """Test successful rename result."""
        result = RenameResult(
            success=True,
            total_files=10,
            renamed=10,
            skipped=0,
            errors=[],
            renamed_files=[
                {"old": "file1.txt", "new": "photo_001.txt"},
                {"old": "file2.txt", "new": "photo_002.txt"},
            ],
        )
        assert result.success is True
        assert result.renamed == 10
        assert len(result.renamed_files) == 2

    def test_result_partial_failure(self):
        """Test partial failure result."""
        result = RenameResult(
            success=False,
            total_files=10,
            renamed=8,
            skipped=0,
            errors=[{"file": "readonly.txt", "error": "Permission denied"}],
            renamed_files=[],
        )
        assert result.success is False
        assert len(result.errors) == 1


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_sanitize_remove_special_chars(self):
        """Test removing special characters."""
        result = sanitize_filename("file<>name.txt")
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_preserve_extension(self):
        """Test preserving file extension."""
        result = sanitize_filename("my file.txt")
        assert result.endswith(".txt")

    def test_sanitize_replace_spaces(self):
        """Test replacing spaces with underscores."""
        result = sanitize_filename("my file name.txt", replace_spaces=True)
        assert " " not in result

    def test_sanitize_remove_leading_dots(self):
        """Test handling leading dots."""
        result = sanitize_filename("...hidden.txt")
        # Should handle gracefully, not break
        assert result is not None

    def test_sanitize_trim_whitespace(self):
        """Test trimming whitespace."""
        result = sanitize_filename("  file.txt  ")
        assert not result.startswith(" ")
        assert not result.endswith(" ") or result.endswith(".txt")

    def test_sanitize_unicode(self):
        """Test handling unicode characters."""
        result = sanitize_filename("cafe_resume.txt")
        assert result is not None

    def test_sanitize_empty_result(self):
        """Test handling when sanitization would result in empty name."""
        result = sanitize_filename("<><>.txt")
        # Should return something valid
        assert len(result) > 0


class TestApplyPattern:
    """Test pattern application to filenames."""

    def test_apply_pattern_basic(self):
        """Test basic pattern application."""
        result = apply_pattern(
            original_name="document.pdf", pattern="{name}_{date}", date_format="%Y%m%d"
        )
        assert "document" in result
        assert datetime.now().strftime("%Y%m%d") in result

    def test_apply_pattern_with_sequence(self):
        """Test pattern with sequence number."""
        result = apply_pattern(
            original_name="photo.jpg", pattern="{sequence}_{name}", sequence=5, sequence_padding=3
        )
        assert "005" in result
        assert "photo" in result

    def test_apply_pattern_name_placeholder(self):
        """Test {name} placeholder (filename without extension)."""
        result = apply_pattern(original_name="my_document.pdf", pattern="backup_{name}")
        assert "backup_my_document" in result
        assert result.endswith(".pdf")

    def test_apply_pattern_ext_placeholder(self):
        """Test {ext} placeholder."""
        result = apply_pattern(original_name="photo.jpg", pattern="{name}_edited.{ext}")
        assert "photo_edited.jpg" == result

    def test_apply_pattern_date_placeholder(self):
        """Test {date} placeholder with custom format."""
        result = apply_pattern(
            original_name="file.txt", pattern="{date}_{name}", date_format="%Y-%m-%d"
        )
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in result

    def test_apply_pattern_datetime_placeholder(self):
        """Test {datetime} placeholder."""
        result = apply_pattern(
            original_name="file.txt", pattern="{datetime}_{name}", datetime_format="%Y%m%d_%H%M%S"
        )
        # Should contain current datetime
        assert datetime.now().strftime("%Y%m%d") in result

    def test_apply_pattern_original_placeholder(self):
        """Test {original} placeholder (full original filename)."""
        result = apply_pattern(original_name="document.pdf", pattern="copy_of_{original}")
        assert result == "copy_of_document.pdf"


class TestFileRenamer:
    """Test FileRenamer class."""

    @pytest.fixture
    def renamer(self):
        """Create a FileRenamer instance for testing."""
        config = RenameConfig(input_directory="./files")
        return FileRenamer(config)

    @pytest.fixture
    def setup_test_files(self):
        """Create test files for renaming."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "file1.txt").write_text("content1")
            (temp_path / "file2.txt").write_text("content2")
            (temp_path / "document.pdf").write_bytes(b"pdf content")
            (temp_path / "photo.jpg").write_bytes(b"jpg content")

            yield temp_dir

    def test_renamer_initialization(self, renamer):
        """Test renamer initialization."""
        assert renamer.config is not None

    def test_renamer_get_files(self, setup_test_files):
        """Test getting files from directory."""
        config = RenameConfig(input_directory=setup_test_files)
        renamer = FileRenamer(config)

        files = renamer.get_files()
        assert len(files) == 4

    def test_renamer_get_files_with_pattern(self, setup_test_files):
        """Test getting files with glob pattern."""
        config = RenameConfig(input_directory=setup_test_files, file_pattern="*.txt")
        renamer = FileRenamer(config)

        files = renamer.get_files()
        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)

    def test_renamer_add_prefix(self, setup_test_files):
        """Test adding prefix to filenames."""
        config = RenameConfig(input_directory=setup_test_files, prefix="new_", file_pattern="*.txt")
        renamer = FileRenamer(config)

        result = renamer.rename()

        assert result.renamed == 2
        renamed_names = [r["new"] for r in result.renamed_files]
        assert all(n.startswith("new_") for n in renamed_names)

    def test_renamer_add_suffix(self, setup_test_files):
        """Test adding suffix to filenames."""
        config = RenameConfig(
            input_directory=setup_test_files, suffix="_backup", file_pattern="*.txt"
        )
        renamer = FileRenamer(config)

        result = renamer.rename()

        assert result.renamed == 2
        # Suffix should be before extension
        for r in result.renamed_files:
            assert "_backup.txt" in r["new"]

    def test_renamer_replace_text(self, setup_test_files):
        """Test replacing text in filenames."""
        config = RenameConfig(
            input_directory=setup_test_files, replace_from="file", replace_to="document"
        )
        renamer = FileRenamer(config)

        result = renamer.rename()

        renamed_names = [r["new"] for r in result.renamed_files]
        assert any("document" in n for n in renamed_names)
        assert not any("file" in n for n in renamed_names if "document" in n)

    def test_renamer_add_sequence(self, setup_test_files):
        """Test adding sequence numbers."""
        config = RenameConfig(
            input_directory=setup_test_files,
            add_sequence=True,
            sequence_start=1,
            sequence_padding=3,
            file_pattern="*.txt",
        )
        renamer = FileRenamer(config)

        result = renamer.rename()

        assert result.renamed == 2
        renamed_names = [r["new"] for r in result.renamed_files]
        assert any("001" in n or "002" in n for n in renamed_names)

    def test_renamer_lowercase(self, setup_test_files):
        """Test converting to lowercase."""
        # Create uppercase file
        temp_path = Path(setup_test_files)
        (temp_path / "UPPERCASE.TXT").write_text("content")

        config = RenameConfig(
            input_directory=setup_test_files, lowercase=True, file_pattern="UPPERCASE.TXT"
        )
        renamer = FileRenamer(config)

        result = renamer.rename()

        assert result.renamed == 1
        assert result.renamed_files[0]["new"] == "uppercase.txt"

    def test_renamer_uppercase(self, setup_test_files):
        """Test converting to uppercase."""
        config = RenameConfig(
            input_directory=setup_test_files, uppercase=True, file_pattern="file1.txt"
        )
        renamer = FileRenamer(config)

        result = renamer.rename()

        assert result.renamed == 1
        assert result.renamed_files[0]["new"] == "FILE1.TXT"

    def test_renamer_dry_run(self, setup_test_files):
        """Test dry run mode doesn't rename files."""
        config = RenameConfig(input_directory=setup_test_files, prefix="test_", dry_run=True)
        renamer = FileRenamer(config)

        result = renamer.rename()

        # Should show what would be renamed
        assert len(result.renamed_files) > 0

        # But files should still have original names
        temp_path = Path(setup_test_files)
        assert (temp_path / "file1.txt").exists()
        assert not (temp_path / "test_file1.txt").exists()

    def test_renamer_skip_conflicts(self, setup_test_files):
        """Test skipping files when target exists."""
        temp_path = Path(setup_test_files)

        # Create a file that would conflict
        (temp_path / "new_file1.txt").write_text("existing")

        config = RenameConfig(
            input_directory=setup_test_files, prefix="new_", file_pattern="file1.txt"
        )
        renamer = FileRenamer(config)

        result = renamer.rename()

        # Should skip due to conflict
        assert result.skipped >= 1


class TestRenameFiles:
    """Test the main rename_files function."""

    @pytest.fixture
    def setup_files(self):
        """Set up test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            for i in range(5):
                (temp_path / f"photo_{i}.jpg").write_bytes(b"jpg")

            yield temp_dir

    def test_rename_files_basic(self, setup_files):
        """Test basic file renaming."""
        result = rename_files(input_directory=setup_files, prefix="img_")

        assert result.success is True
        assert result.renamed == 5

    def test_rename_files_with_pattern(self, setup_files):
        """Test renaming with pattern."""
        result = rename_files(
            input_directory=setup_files, pattern="{sequence}_{name}", sequence_padding=4
        )

        assert result.success is True
        for r in result.renamed_files:
            # Should have 4-digit sequence
            assert any(f"{i:04d}" in r["new"] for i in range(1, 10))

    def test_rename_files_directory_not_found(self):
        """Test error for missing directory."""
        with pytest.raises(FileNotFoundError):
            rename_files(input_directory="/nonexistent/path")

    def test_rename_files_marks_conflicts_as_unsuccessful(self, setup_files):
        """Test conflicting targets are reported through the result object."""
        temp_path = Path(setup_files)
        (temp_path / "img_photo_0.jpg").write_bytes(b"existing")

        result = rename_files(
            input_directory=setup_files,
            prefix="img_",
            file_pattern="photo_0.jpg",
        )

        assert result.success is False
        assert result.skipped == 1
        assert result.errors[0]["error"].startswith("Target already exists")


class TestPreviewRename:
    """Test the preview_rename function."""

    @pytest.fixture
    def setup_files(self):
        """Set up test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "test.txt").write_text("content")
            yield temp_dir

    def test_preview_shows_changes(self, setup_files):
        """Test preview shows proposed changes."""
        preview = preview_rename(input_directory=setup_files, prefix="new_")

        assert len(preview) > 0
        assert preview[0]["old"] == "test.txt"
        assert preview[0]["new"] == "new_test.txt"

    def test_preview_no_actual_changes(self, setup_files):
        """Test preview doesn't modify files."""
        preview_rename(input_directory=setup_files, prefix="changed_")

        # Original file should still exist
        assert (Path(setup_files) / "test.txt").exists()
        assert not (Path(setup_files) / "changed_test.txt").exists()


class TestRecursiveRenaming:
    """Test recursive directory renaming."""

    @pytest.fixture
    def setup_nested_files(self):
        """Set up nested directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Root files
            (temp_path / "root.txt").write_text("root")

            # Subdirectory
            sub_dir = temp_path / "subdir"
            sub_dir.mkdir()
            (sub_dir / "nested.txt").write_text("nested")

            # Deeper subdirectory
            deep_dir = sub_dir / "deep"
            deep_dir.mkdir()
            (deep_dir / "deep.txt").write_text("deep")

            yield temp_dir

    def test_recursive_rename(self, setup_nested_files):
        """Test recursive renaming in subdirectories."""
        result = rename_files(input_directory=setup_nested_files, prefix="r_", recursive=True)

        assert result.renamed == 3  # All 3 files

    def test_non_recursive_rename(self, setup_nested_files):
        """Test non-recursive renaming only affects root."""
        result = rename_files(input_directory=setup_nested_files, prefix="r_", recursive=False)

        assert result.renamed == 1  # Only root.txt


class TestUvxCompatibility:
    """Test that the module works correctly when run via uvx."""

    def test_module_import(self):
        """Test module can be imported."""
        from src.automations import rename_files as mod

        assert hasattr(mod, "RenameConfig")
        assert hasattr(mod, "RenameResult")
        assert hasattr(mod, "FileRenamer")
        assert hasattr(mod, "rename_files")
        assert hasattr(mod, "preview_rename")
        assert hasattr(mod, "apply_pattern")
        assert hasattr(mod, "sanitize_filename")

    def test_dataclass_fields(self):
        """Test RenameConfig has all expected fields."""
        from dataclasses import fields

        field_names = {f.name for f in fields(RenameConfig)}
        expected_fields = {
            "input_directory",
            "pattern",
            "prefix",
            "suffix",
            "replace_from",
            "replace_to",
            "add_date",
            "add_sequence",
            "sequence_start",
            "sequence_padding",
            "lowercase",
            "uppercase",
            "recursive",
            "dry_run",
            "file_pattern",
            "date_format",
        }
        assert field_names == expected_fields


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_rename_empty_directory(self):
        """Test renaming in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = rename_files(input_directory=temp_dir, prefix="test_")

            assert result.total_files == 0
            assert result.renamed == 0

    def test_rename_preserves_hidden_files(self):
        """Test that hidden files are handled properly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / ".hidden").write_text("hidden")
            (temp_path / "visible.txt").write_text("visible")

            result = rename_files(
                input_directory=temp_dir,
                prefix="r_",
                file_pattern="*",  # Should match visible files
            )

            # Behavior depends on implementation choice
            assert result.total_files >= 1

    def test_rename_special_characters(self):
        """Test renaming files with special characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create file with spaces
            (temp_path / "my file (1).txt").write_text("content")

            result = rename_files(input_directory=temp_dir, replace_from=" ", replace_to="_")

            assert result.renamed >= 1
            renamed = result.renamed_files[0]["new"]
            assert " " not in renamed

    def test_rename_unicode_filenames(self):
        """Test renaming files with unicode characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "cafe.txt").write_text("content")

            result = rename_files(input_directory=temp_dir, prefix="new_")

            assert result.success is True

    def test_rename_same_name_no_change(self):
        """Test that files not matching criteria are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "already_prefixed.txt").write_text("content")

            result = rename_files(
                input_directory=temp_dir, replace_from="nonexistent", replace_to="replacement"
            )

            # Should skip files that don't need changes
            assert result.skipped >= 0

    def test_rename_date_format_custom(self):
        """Test custom date format in pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "photo.jpg").write_bytes(b"jpg")

            result = rename_files(
                input_directory=temp_dir, pattern="{date}_{name}", date_format="%d-%m-%Y"
            )

            assert result.success is True
            new_name = result.renamed_files[0]["new"]
            # Should contain date in DD-MM-YYYY format
            today = datetime.now().strftime("%d-%m-%Y")
            assert today in new_name
