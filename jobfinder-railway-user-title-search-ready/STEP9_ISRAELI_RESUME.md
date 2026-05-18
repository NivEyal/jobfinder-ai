# Step 9 - Israeli Resume Template

This step replaces the old generic resume template with an Israeli bilingual template.

## What changed

- `plain_text_resume.yaml` now uses `resume_metadata.template: israeli_resume`.
- The template has Hebrew and English versions in one file.
- Hebrew uses `direction: rtl`.
- English uses `direction: ltr`.
- Israeli phone number and Israeli city are first-class fields.
- LinkedIn is optional and not required.
- GitHub and portfolio are optional supported links.
- US/EU legal authorization and unrelated self-identification fields were removed from the active template.

## Required contact fields

```yaml
personal_information:
  first_name: "שם פרטי"
  last_name: "שם משפחה"
  email: "candidate@example.com"
  phone: "+972-50-123-4567"
  city: "תל אביב"
  country: Israel
```

Optional links:

```yaml
github: "https://github.com/your-user"
portfolio: "https://your-portfolio.example.com"
linkedin: ""
```

## Versions

```yaml
versions:
  he:
    direction: rtl
  en:
    direction: ltr
```

The runtime validates the Israeli resume template before preparing the static application package.
