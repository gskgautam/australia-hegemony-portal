from werkzeug.security import generate_password_hash
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Australian states and territories (consortium "cultural zones").
# Regions group them for admin filtering only; state/territory is the sampling unit.
REGION_STATE_MAP = {
	"States": ["New South Wales", "Victoria", "Queensland", "South Australia", "Western Australia", "Tasmania"],
	"Territories": ["Northern Territory", "Australian Capital Territory"],
}

COUNTRY = "Australia"

# Usernames of onboarded annotators, mapped to their state/territory.
# Fill in as annotators are recruited (see the staffing register, Part C4).
ONBOARDED_ANNOTATOR_USERNAMES_STATES = {
	# "annotator_username": "New South Wales",
}
ONBOARDED_ANNOTATOR_USERNAMES = ["admin", *ONBOARDED_ANNOTATOR_USERNAMES_STATES.keys()]

# Inter-annotator review: 3 annotators per jurisdiction; each item is reviewed
# blind by the other two. Keys are lower-case state names.
# "seed" makes the review sampling reproducible.
STATE_REVIEW_ASSIGNMENT_CONFIGS = {
	# "new south wales": {
	# 	"seed": "iaa-nsw-v1",
	# 	"annotators": ["nsw_a1", "nsw_a2", "nsw_a3"],
	# 	"per_annotator_quota": {"nsw_a1": 21, "nsw_a2": 21, "nsw_a3": 21},
	# },
}

HEGEMONY_AXES = [
	"social",
	"economic",
	"religious",
	"gender",
	"linguistic",
	"colorism",
]

# The four consortium models (decided 19 Oct 2026), all called through OpenRouter.
# "key" is the internal/storage name; "label" is what annotators see (models are anonymised).
# "review_slot" maps to the IAA database columns (model1..model4).
MODELS = [
	{"key": "llama4maverick", "label": "Model 1", "review_slot": "model1", "openrouter_id": "meta-llama/llama-4-maverick"},
	{"key": "qwen3_8_27b",    "label": "Model 2", "review_slot": "model2", "openrouter_id": "qwen/qwen3.8-27b"},
	{"key": "gptoss120b",     "label": "Model 3", "review_slot": "model3", "openrouter_id": "openai/gpt-oss-120b"},
	{"key": "deepseekv32",    "label": "Model 4", "review_slot": "model4", "openrouter_id": "deepseek/deepseek-v3.2"},
]
MODEL_KEYS = [m["key"] for m in MODELS]

# Australia collects base prompts only: identity-primed prompts were dropped
# consortium-wide (11 Nov 2026), and English-official countries skip translated prompts (9 Nov 2026).
PROMPT_TYPES = ["base"]

# Shared inference settings (#resources, 29 Oct 2026). Temperature and max tokens are
# intentionally unset (provider defaults); the word limit is enforced by the prompt.
SYSTEM_PROMPT = "Answer in no more than 150 words in English."
ENABLE_REASONING = True

DB_PATH = BASE_DIR / "data" / "annotations.db"

API_KEYS_PATH = BASE_DIR / "accounts" / "apikeys.json"

with open(API_KEYS_PATH, "r") as f:
	KEYS = json.load(f)


def _model_headers():
	headers = []
	for model_key in MODEL_KEYS:
		for kind in PROMPT_TYPES:
			prefix = f"{model_key}_{kind}"
			headers += [f"{prefix}_output", f"{prefix}_hallucination"]
			for axis in HEGEMONY_AXES:
				headers += [f"{prefix}_{axis}", f"{prefix}_{axis}_impact"]
	return headers


# Flat column order used for CSV export.
HEADERS = [
	"id",
	"timestamp",
	"annotator_name",
	"country",
	"region",
	"state",
	"base_prompt",
	*_model_headers(),
	"ground_truth",
	"references",
	"expert_reviews",
	"isAccept",
	"annotator_addressed",
]
