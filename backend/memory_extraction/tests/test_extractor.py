import pytest
from pydantic import ValidationError

from memory_extraction.extractor import MemoryExtractor, ExtractionError
from memory_extraction.schemas import ExtractionRequest, MemoryType
from memory_extraction.decision_extractor import extract_decisions
from memory_extraction.commitment_extractor import extract_commitments


class FakeLLM:
    def __init__(self, result):
        self.result = result

    def generate_json(self, text, filename=None, source_type=None):
        return self.result


def request(text="We decided to use React."):
    return ExtractionRequest(
        company_id="company-1",
        source_id="source-1",
        extracted_text=text,
        filename="meeting.txt",
        source_type="meeting",
    )


def test_extract_decision_and_commitment():
    fake = FakeLLM({
        "memories": [
            {
                "memory_type": "decision",
                "title": "Frontend framework selected",
                "content": "The team decided to use React for the frontend.",
                "confidence": 0.94,
                "tags": ["frontend", "react"],
                "entities": [{"entity_type": "other", "name": "React"}],
                "meta_info": {},
            },
            {
                "memory_type": "employee_commitment",
                "title": "Proposal submission",
                "content": "Priya will send the project proposal by Monday.",
                "person": "Priya",
                "deadline": "Monday",
                "confidence": 0.91,
                "tags": ["proposal"],
                "entities": [{"entity_type": "person", "name": "Priya"}],
                "meta_info": {"task": "Send the project proposal"},
            },
        ],
        "entities": [{"entity_type": "person", "name": "Priya"}],
    })
    result = MemoryExtractor(fake).extract(request())
    assert result.memories_count == 2
    assert result.memories[0].memory_type == MemoryType.DECISION
    assert len(extract_decisions(result.memories)) == 1
    assert len(extract_commitments(result.memories)) == 1
    assert result.memories[1].person == "Priya"
    assert result.memories[1].deadline == "Monday"
    assert result.module3_payloads[1]["memory_type"] == "employee_commitment"
    assert result.module3_payloads[1]["meta_info"]["task"] == "Send the project proposal"


def test_multiple_types_and_entity_deduplication():
    fake = FakeLLM({
        "memories": [{
            "memory_type": "client_requirement",
            "title": "Single sign-on",
            "content": "The client requires single sign-on.",
            "company": "Acme",
            "confidence": 0.9,
            "tags": [],
            "entities": [{"entity_type": "company", "name": "Acme"}],
            "meta_info": {},
        }],
        "entities": [{"entity_type": "company", "name": "Acme"}],
    })
    result = MemoryExtractor(fake).extract(request("Client requires SSO."))
    assert result.memories_count == 1
    assert len(result.entities) == 1


def test_empty_extraction_is_valid():
    result = MemoryExtractor(FakeLLM({"memories": [], "entities": []})).extract(request())
    assert result.memories == []
    assert result.memories_count == 0


def test_invalid_memory_type_is_rejected():
    fake = FakeLLM({
        "memories": [{
            "memory_type": "random_type",
            "title": "Some title",
            "content": "Some content",
            "confidence": 0.8,
        }],
        "entities": [],
    })
    with pytest.raises(ExtractionError):
        MemoryExtractor(fake).extract(request())


def test_invalid_confidence_is_rejected():
    fake = FakeLLM({
        "memories": [{
            "memory_type": "decision",
            "title": "Some decision",
            "content": "A decision was made.",
            "confidence": 1.5,
        }],
        "entities": [],
    })
    with pytest.raises(ExtractionError):
        MemoryExtractor(fake).extract(request())


def test_module3_payload_mapping():
    fake = FakeLLM({
        "memories": [{
            "memory_type": "employee_commitment",
            "title": "Send proposal",
            "content": "Priya will send the proposal by Friday.",
            "person": "Priya",
            "deadline": "Friday",
            "confidence": 0.9,
            "tags": ["proposal"],
            "entities": [{"entity_type": "person", "name": "Priya"}],
            "meta_info": {"task": "Send proposal"},
        }],
        "entities": [],
    })
    req = request()
    result = MemoryExtractor(fake).extract(req)
    payload = result.memories[0].to_memory_create_payload(req)
    assert payload["company_id"] == "company-1"
    assert payload["source_id"] == "source-1"
    assert payload["memory_type"] == "employee_commitment"
    assert payload["meta_info"]["person"] == "Priya"
    assert payload["meta_info"]["deadline"] == "Friday"


def test_blank_input_rejected():
    with pytest.raises(ValidationError):
        request("   ")
def test_missing_memories_field():
    fake = FakeLLM({"entities": []})
    result = MemoryExtractor(fake).extract(request())
    assert result.memories_count == 0


def test_invalid_llm_response_type():
    fake = FakeLLM("This is not JSON")
    with pytest.raises(ExtractionError):
        MemoryExtractor(fake).extract(request())


def test_maximum_input_length():
    from memory_extraction.config import settings

    original_limit = settings.max_input_characters
    try:
        settings.max_input_characters = 10
        with pytest.raises(ExtractionError):
            MemoryExtractor(FakeLLM({"memories": [], "entities": []})).extract(
                request("This text is longer than ten characters.")
            )
    finally:
        settings.max_input_characters = original_limit


def test_entity_deduplication_case_insensitive():
    fake = FakeLLM({
        "memories": [{
            "memory_type": "general_info",
            "title": "Company information",
            "content": "Acme is the company.",
            "confidence": 0.9,
            "entities": [
                {"entity_type": "company", "name": "Acme"},
                {"entity_type": "company", "name": "ACME"}
            ]
        }],
        "entities": []
    })
    result = MemoryExtractor(fake).extract(request())
    assert len(result.entities) == 1