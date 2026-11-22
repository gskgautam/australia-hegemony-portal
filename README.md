# Cultural Hegemony Annotation Portal — Australia

A web portal for the Australian arm of the Cultural Hegemony Consortium. Annotators write neutral
questions about life in their state or territory, collect answers from four AI models, and label
whether each answer presents one group's way of life as the normal, better or required way to be
Australian. They then write a corrective Ground Truth, which is reviewed by a cultural expert and two
peer annotators.

- **Zones:** the 8 states and territories (NSW, VIC, QLD, SA, WA, TAS, NT, ACT)
- **Prompts:** one English base prompt per item (no identity-primed or translated prompts)
- **Models (anonymised as Model 1–4):** Llama 4 Maverick, Qwen3.8-27B, gpt-oss-120b, DeepSeek V3.2
- **Axes:** social, economic, religious, gender, linguistic, colourism
- **Target:** at least 500 accepted items for Australia, about 61–64 per state or territory

---

## For annotators

Open the portal link your coordinator sends you, then:

1. **Sign up** with the access code from your coordinator, and choose your state or territory.
2. Read the **Annotator Handbook** (menu: *Annotator Resources*). The **References** page lists the
   six axes with Yes and No examples.
3. On **Annotate**: write your question, click **Check Similarity**, then **Generate** once for each
   model. Label every answer on all six axes, flag hallucinations, and write the Ground Truth.
4. Click **Review Annotation**, then **Confirm & Submit**. Expert feedback appears on your **Load** page.
5. When items are assigned to you, review your teammates' work under **Review**.

Use **Save Draft** at any time. Never regenerate an answer to get a "better" one.

---

## For administrators

### Requirements

- Python 3.10+
- An [OpenRouter](https://openrouter.ai) API key with credit (about 2,000 calls for 500 items)

### Set up

```bash
git clone https://github.com/gskgautam/australia-hegemony-portal.git
cd australia-hegemony-portal/annotation_app
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p accounts
```

Create `annotation_app/accounts/apikeys.json`. Git ignores this file, so it is never committed.

```json
{
  "FLASK_SECRET_KEY": "<long random string>",
  "OPENROUTER_API_KEY": "<your OpenRouter key>",
  "ADMIN_USERNAME": "admin",
  "ADMIN_PASSWORD_HASH": "<hash of the admin password>",
  "ANNOTATOR_PASSWORD_HASH": "<hash of the sign-up access code>"
}
```

Make the two hashes with:

```bash
.venv/bin/python -c "from werkzeug.security import generate_password_hash as h; print(h(input('Password: ')))"
```

### Run locally

```bash
.venv/bin/python app.py
```

Then open http://127.0.0.1:5000. The app can be started from any folder.

### Host it for annotators

Any host that runs a Python (Flask) web app works. On PythonAnywhere:

1. Use a paid account, because free accounts can only reach an approved list of outside sites.
2. Clone the repo and create the virtualenv as above.
3. Upload `accounts/apikeys.json` with the file manager. Don't commit it.
4. Under *Web*, set the virtualenv path and edit the WSGI file to:
   ```python
   import sys
   sys.path.insert(0, "/home/<your-username>/australia-hegemony-portal/annotation_app")
   from app import app as application
   ```
5. Reload the web app.

If your ethics approval requires data to stay in Australia, use a university server or an Australian
cloud region instead.

### Onboard annotators

All settings are in `annotation_app/config.py`.

| Setting | What to put there |
|---|---|
| `ONBOARDED_ANNOTATOR_USERNAMES_STATES` | Each annotator's username and their state or territory |
| `STATE_REVIEW_ASSIGNMENT_CONFIGS` | For each jurisdiction: its 3 annotators and how many items each reviews |
| `TRAINING_VIDEO_URL`, `TIMESHEET_URL` | Optional menu links; leave empty to hide them |
| `MODELS` | The four models and their OpenRouter IDs |

Reload the web app after changing the config.

### Roles

| Role | Can do |
|---|---|
| Annotator | Write and edit their own items, save notes, review teammates' items in their jurisdiction |
| Admin / cultural expert | See all items, mark them Accepted, Needs Restructuring or Rejected with comments, export CSV, see review statistics |

### Where data is kept

Everything is kept in `annotation_app/data/`, which git ignores:

| File | Contents |
|---|---|
| `annotations.db` | All annotation items (SQLite) |
| `iaa_reviews.db` | Peer-review scores |
| `annotators.json` | Annotator accounts and sign-up details (personal data) |
| `prompt_embeddings.json` | Index used by *Check Similarity* |
| `drafts/` | Unsubmitted drafts and saved notes |

Back up this folder regularly. **Never commit it**, because the repository is public.

### Exports

- *Admin → Download CSV*: all items, one row each
- `/admin/iaa-reviews.csv`: all peer-review scores

---

## Still to do

- Confirm the OpenRouter model IDs with a real key, especially `qwen/qwen3.8-27b`.
- Export in the consortium's upload format once the updated `dataset_format.json` is published.
- The portal follows the consortium's (India team's) workflow. The Australian guidelines document also
  describes steps the portal does not have: expert approval of prompts before generation, blind
  labelling by both teammates, a "Needs review" flag and per-axis confidence. Either run those outside
  the portal or align the guidelines with the portal.

---

*Built on the consortium's shared annotation portal code. Please cite the consortium study when using this tool.*
