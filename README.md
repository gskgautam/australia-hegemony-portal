# Cultural Hegemony Annotation Portal — Australia

**Portal:** https://culturalhegemony.pythonanywhere.com

The Australian annotation portal of the Cultural Hegemony Consortium. Annotators write a neutral
question about their state or territory, get answers from four AI models, label each answer for
cultural hegemony, and write a corrective Ground Truth. A cultural expert and peer annotators review
each item.

| | |
|---|---|
| Zones | NSW, VIC, QLD, SA, WA, TAS, NT, ACT |
| Models (shown as Model 1–4) | Llama 4 Maverick, Qwen3.8-27B, gpt-oss-120b, DeepSeek V3.2 (via OpenRouter) |
| Axes | Social, economic, religious, gender, linguistic, colourism |
| Target | 500+ accepted items (about 61–64 per state or territory) |

---

## For annotators

1. Open the portal and choose **Create account**. Enter the access code from your coordinator and
   pick your state or territory.
2. Read the **Annotator Handbook** and **References** (menu: *Annotator Resources*).
3. On **Annotate**: write your question → **Check Similarity** → **Generate** for each model → label
   all six axes for every answer → flag hallucinations → write the Ground Truth with references.
4. **Review Annotation** → **Confirm & Submit**. Expert feedback appears on your **Load** page.
5. Review teammates' items under **Review** when they are assigned to you.

Use **Save Draft** at any time. Never regenerate an answer to get a different one.

---

## For administrators

### Update the live site

In a PythonAnywhere Bash console:

```bash
cd ~/australia-hegemony-portal && git pull
```

Then click **Reload** on the Web tab. Data and keys are not touched.

### Onboard annotators

Edit `annotation_app/config.py`, then reload:

| Setting | What to put there |
|---|---|
| `ONBOARDED_ANNOTATOR_USERNAMES_STATES` | Each annotator's username and state or territory |
| `STATE_REVIEW_ASSIGNMENT_CONFIGS` | Each jurisdiction's 3 annotators and how many items each reviews |
| `TRAINING_VIDEO_URL`, `TIMESHEET_URL` | Optional menu links (empty = hidden) |

### Data and exports

All data is in `annotation_app/data/` on the server. Git ignores this folder, and it must never be
committed, because the repository is public.

- `annotations.db`: annotation items
- `iaa_reviews.db`: peer-review scores
- `annotators.json`: accounts and sign-up details (personal data)

Exports: **Admin → Download CSV** (all items) and `/admin/iaa-reviews.csv` (peer reviews).
Back up the `data/` folder regularly.

### Change keys or passwords

```bash
cd ~/australia-hegemony-portal/annotation_app
~/.virtualenvs/hegemony/bin/python scripts/make_keys.py
```

The script asks for the admin password, the annotator access code and the OpenRouter API key. Typing
is hidden, and it stores only hashes of the passwords. Reload afterwards.

### Set up from scratch (new server)

```bash
git clone https://github.com/gskgautam/australia-hegemony-portal.git
cd australia-hegemony-portal/annotation_app
python3.12 -m venv ~/.virtualenvs/hegemony
~/.virtualenvs/hegemony/bin/pip install -r requirements.txt
~/.virtualenvs/hegemony/bin/python scripts/make_keys.py
```

On PythonAnywhere, add a web app (**Manual configuration**, **Python 3.12**). Set the virtualenv to
`/home/<user>/.virtualenvs/hegemony`, turn on **Force HTTPS**, and replace the WSGI file with:

```python
import sys
sys.path.insert(0, "/home/<user>/australia-hegemony-portal/annotation_app")
from app import app as application
```

To run it locally instead: `~/.virtualenvs/hegemony/bin/python app.py`, then open http://127.0.0.1:5000.

---

## Still to do

- Export in the consortium upload format once the updated `dataset_format.json` is published.
- Delete the dry-run data (`annotation_app/data/`) before the pilot starts.

*Built on the consortium's shared annotation portal code. Please cite the consortium study when using this tool.*
