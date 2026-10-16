# Cloud-only Indic Parler voice evaluation

This one-off test runs on a temporary Google Cloud `g2-standard-4` L4 VM in
`asia-south1`. The VM reads the rotated Hugging Face token from Secret Manager
at runtime. The model and cache stay on the VM; only two short Telugu voice
samples and a JSON timing report are uploaded to a private Mumbai bucket.

The startup script shuts the VM down after the test, including failures. The
operator must still delete the stopped VM to remove its boot disk. The bucket
deletes its objects after seven days. Do not commit tokens or model weights.

The sample compares the model card's recommended Telugu speakers, Lalitha and
Prakash. It is an inference and listening test, not fine-tuning or a claim of
production voice quality. Native-speaker review should precede integration.

On 14 October 2026, Compute Engine rejected the L4 VM request because the
project's billing account was still on the free tier, which does not allow
non-TPU accelerators. No VM was created and no Indic Parler sample was run.
The private bucket and service account remain staged for a future run after
the billing account is upgraded. Do not try to run the model on the laptop.

As a cloud-only interim voice path, the backend supports
`TTS_PROVIDER=google_chirp`. This uses Google Cloud's managed Chirp 3 HD voices
and requires ADC plus `GOOGLE_CLOUD_PROJECT=ayana-video-studio`. The product
owner approved the female and male Telugu samples. Sentence breaks receive a
short natural pause, based on a separately approved listening sample. The
local ignored `backend/.env` and deployment example select this provider;
the code default remains Edge TTS if it is not configured.
