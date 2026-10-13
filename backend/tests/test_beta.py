"""No provider calls or database credentials needed."""
import unittest
from unittest.mock import MagicMock, patch

import cloud_storage
import ram_ai
from prepare_tuning_data import prepare


class CloudStorageTests(unittest.TestCase):
    def test_rejects_ambiguous_paths(self):
        for path in ("", "../private", "/absolute", "a//b", "a/./b", "a\\b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                cloud_storage.validate_object_name(path)

    def test_upload_keeps_content_type_and_prevents_overwrite(self):
        client = MagicMock()
        with patch.object(cloud_storage, "client", return_value=client):
            result = cloud_storage.upload("private-bucket", "vidbharat/audio/u/a.mp3", b"audio", "audio/mpeg")
        self.assertEqual(result["path"], "vidbharat/audio/u/a.mp3")
        client.bucket.assert_called_once_with("private-bucket")
        client.bucket.return_value.blob.return_value.upload_from_string.assert_called_once_with(
            b"audio", content_type="audio/mpeg", if_generation_match=0, timeout=120)

    def test_hook_check_does_not_claim_measured_seconds(self):
        passed, detail = ram_ai.check_hook_pacing([{"narration": "A small village learns to share its water"}])
        self.assertTrue(passed)
        self.assertIn("duration must be checked", detail)

    def test_training_excludes_unreviewed_outputs(self):
        with self.assertRaises(ValueError):
            prepare([{"split": "train", "prompt": "topic", "response": "generated"}])

    def test_training_and_validation_cannot_share_prompts(self):
        rows = [{"split": split, "prompt": "same topic", "response": "corrected",
                 "reviewed": True, "permission_to_train": True} for split in ("train", "validation")]
        with self.assertRaises(ValueError):
            prepare(rows)

    def test_reviewed_examples_export_provider_format(self):
        rows = [{"split": split, "prompt": split + " topic", "response": {"title": "కథ"},
                 "reviewed": True, "permission_to_train": True} for split in ("train", "validation")]
        result = prepare(rows)
        self.assertEqual(result["train"][0]["contents"][1]["role"], "model")
        self.assertIn("కథ", result["train"][0]["contents"][1]["parts"][0]["text"])


if __name__ == "__main__":
    unittest.main()
