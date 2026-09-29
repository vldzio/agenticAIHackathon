from app.llm.mock import MockLLMClient
from app.schemas.profile import ProfileIn
from app.services import assessment_service as svc
from app.services import export_service
from tests.conftest import BASE_PROFILE


def make(**patch):
    return svc.run_to_completion(MockLLMClient(), ProfileIn(**{**BASE_PROFILE, **patch}), mode="mock")


def test_ics_structure_and_escaping():
    a = make(user_name="Semi;colon, Name")
    ics = export_service.to_ics(a)
    assert ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n")
    assert "RRULE:FREQ=WEEKLY;COUNT=" in ics and "BYDAY=" in ics
    unfolded = ics.replace("\r\n ", "")
    assert "\\n- " in unfolded  # newlines in DESCRIPTION are escaped
    assert all(len(line.encode()) <= 75 for line in ics.split("\r\n"))


def test_ics_uses_preferred_time():
    a = make(available_hours_per_week="4 hours, evenings")
    assert "T183000" in export_service.to_ics(a)


def test_pdf_flags_clearance_and_simulation():
    a = make(age=68, health_conditions="heart attack last year")
    pdf = export_service.to_pdf(a)
    assert pdf.startswith(b"%PDF") and len(pdf) > 2000
    assert a.safety.requires_clearance
