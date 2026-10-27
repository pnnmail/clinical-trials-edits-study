"""Stage 1 (step 1): the list of trials matching the spec filter via API v2 -> data/trials.parquet.
Raw response pages -> raw/_list/{date}/page_NNN.json (never modified)."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CFG, DATA, RAW, TODAY, ctgov_client, get_logger  # noqa: E402

log = get_logger("list_trials")
FIELDS = ["NCTId", "BriefTitle", "LeadSponsorName", "LeadSponsorClass", "Phase", "OverallStatus",
          "StudyFirstPostDate", "LastUpdatePostDate", "PrimaryCompletionDate", "EnrollmentCount"]


def main():
    c = ctgov_client()
    out_dir = RAW / "_list" / TODAY
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, token, page = [], None, 0
    while True:
        params = {"filter.advanced": CFG["trials"]["filter_advanced"], "pageSize": 1000, "countTotal": "true",
                  "fields": ",".join(FIELDS)}
        if token:
            params["pageToken"] = token
        r = c.get("https://clinicaltrials.gov/api/v2/studies", params=params)
        j = r.json()
        (out_dir / f"page_{page:03d}.json").write_text(r.text, encoding="utf-8")
        for s in j.get("studies", []):
            p = s["protocolSection"]
            ident, st = p["identificationModule"], p.get("statusModule", {})
            sp = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
            des = p.get("designModule", {})
            rows.append(dict(nct_id=ident["nctId"], title=ident.get("briefTitle"), sponsor=sp.get("name"),
                             sponsor_class=sp.get("class"), phases=",".join(des.get("phases", [])),
                             status=st.get("overallStatus"),
                             first_posted=(st.get("studyFirstPostDateStruct") or {}).get("date"),
                             last_posted=(st.get("lastUpdatePostDateStruct") or {}).get("date"),
                             primary_completion=(st.get("primaryCompletionDateStruct") or {}).get("date"),
                             enrollment=(des.get("enrollmentInfo") or {}).get("count")))
        page += 1
        if page == 1:
            log.info("total matching the filter: %s", j.get("totalCount"))
        token = j.get("nextPageToken")
        if not token:
            break
    df = pd.DataFrame(rows).drop_duplicates("nct_id")
    df.to_parquet(DATA / "trials.parquet", index=False)
    log.info("trials: %d, sponsors: %d", len(df), df.sponsor.nunique())


if __name__ == "__main__":
    main()
