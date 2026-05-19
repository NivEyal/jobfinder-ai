import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


ISRAELI_PHONE_RE = re.compile(r"^(?:\+972|0)(?:[-\s]?\d){8,10}$")
SUPPORTED_LANGUAGES = {"he", "en"}
RTL_LANGUAGES = {"he"}


class IsraeliResumeError(ValueError):
    pass


@dataclass(frozen=True)
class IsraeliResume:
    data: Dict[str, Any]

    @classmethod
    def from_yaml(cls, yaml_text: str) -> "IsraeliResume":
        data = yaml.safe_load(yaml_text) or {}
        resume = cls(data=data)
        resume.validate()
        return resume

    @classmethod
    def from_path(cls, path: str | Path) -> "IsraeliResume":
        return cls.from_yaml(Path(path).read_text(encoding="utf-8"))

    def validate(self):
        metadata = self.data.get("resume_metadata", {})
        personal = self.data.get("personal_information", {})
        versions = self.data.get("versions", {})

        if metadata.get("template") != "israeli_resume":
            raise IsraeliResumeError("resume_metadata.template must be israeli_resume")
        if metadata.get("default_language") not in SUPPORTED_LANGUAGES:
            raise IsraeliResumeError("resume_metadata.default_language must be he or en")

        required_personal = ["first_name", "last_name", "email", "phone", "city", "country"]
        missing = [field for field in required_personal if not personal.get(field)]
        if missing:
            raise IsraeliResumeError(f"Missing personal information fields: {missing}")

        if personal.get("country") != "Israel":
            raise IsraeliResumeError("Israeli resume template expects personal_information.country: Israel")
        if not ISRAELI_PHONE_RE.match(str(personal.get("phone", ""))):
            raise IsraeliResumeError("personal_information.phone must be an Israeli phone number")

        for url_field in ["linkedin", "github", "portfolio"]:
            value = personal.get(url_field)
            if value and not str(value).startswith(("http://", "https://")):
                raise IsraeliResumeError(f"personal_information.{url_field} must be a URL when provided")

        for language in metadata.get("supported_languages", []):
            if language not in SUPPORTED_LANGUAGES:
                raise IsraeliResumeError(f"Unsupported resume language: {language}")
            if language not in versions:
                raise IsraeliResumeError(f"Missing versions.{language}")
            self._validate_version(language, versions[language])

    def _validate_version(self, language: str, version: Dict[str, Any]):
        expected_direction = "rtl" if language in RTL_LANGUAGES else "ltr"
        if version.get("direction") != expected_direction:
            raise IsraeliResumeError(f"versions.{language}.direction must be {expected_direction}")
        for field_name in ["headline", "summary"]:
            if not version.get(field_name):
                raise IsraeliResumeError(f"versions.{language}.{field_name} is required")
        for list_name in ["skills", "education_details", "experience_details", "projects", "languages"]:
            if list_name not in version or not isinstance(version[list_name], list):
                raise IsraeliResumeError(f"versions.{language}.{list_name} must be a list")

    def version(self, language: str | None = None) -> Dict[str, Any]:
        selected = language or self.data["resume_metadata"]["default_language"]
        if selected not in self.data["versions"]:
            raise IsraeliResumeError(f"Resume version not found: {selected}")
        return self.data["versions"][selected]

    def render_text(self, language: str | None = None) -> str:
        selected = language or self.data["resume_metadata"]["default_language"]
        version = self.version(selected)
        personal = self.data["personal_information"]
        lines = [
            f"{personal['first_name']} {personal['last_name']}",
            version["headline"],
            f"{personal['city']}, {personal['country']} | {personal['phone']} | {personal['email']}",
        ]
        optional_links = [personal.get("github"), personal.get("portfolio"), personal.get("linkedin")]
        links = [link for link in optional_links if link]
        if links:
            lines.append(" | ".join(links))
        lines.extend(["", version["summary"], ""])
        lines.append("Skills" if selected == "en" else "כישורים")
        lines.append(", ".join(version["skills"]))
        for section_name in ["experience_details", "education_details", "projects", "languages"]:
            items = version.get(section_name, [])
            if not items:
                continue
            lines.extend(["", section_title(section_name, selected)])
            for item in items:
                lines.append(format_item(item))
        return "\n".join(lines).strip()


def section_title(section_name: str, language: str) -> str:
    titles = {
        "experience_details": {"he": "ניסיון", "en": "Experience"},
        "education_details": {"he": "השכלה", "en": "Education"},
        "projects": {"he": "פרויקטים", "en": "Projects"},
        "languages": {"he": "שפות", "en": "Languages"},
    }
    return titles[section_name][language]


def format_item(item: Any) -> str:
    if isinstance(item, dict):
        values: List[str] = [str(value) for value in item.values() if value not in (None, "", [])]
        return "- " + " | ".join(values)
    return f"- {item}"
