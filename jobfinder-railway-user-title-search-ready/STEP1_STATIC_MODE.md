# Step 1: Static Israel-Oriented Application Mode

This version disables the original assumptions around LinkedIn, Easy Apply, and AI-generated application content.

What changed:

- `main.py` no longer imports or calls the LLM resume/cover-letter builders.
- `secrets.yaml` is no longer required by the runtime and no API key is needed.
- Application output is prepared from fixed local files:
  - `data_folder/plain_text_resume.yaml`
  - `data_folder/cover_letter_template.txt`
- LinkedIn is no longer part of the required resume schema or example resume data.
- AI/LLM dependencies were removed from `requirements.txt`.

Run:

```bash
python main.py
```

The static files will be copied to `data_folder/output`.
