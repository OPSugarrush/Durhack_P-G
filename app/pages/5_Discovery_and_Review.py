import streamlit as st

from _common import family_names, page, require_analysis, show_df, synthetic_banner
from needstate.ai.llm import describe_candidate
from needstate.reliability import review_queue as rq

page("Discovery and Human Review", "🧪")
an = require_analysis()
synthetic_banner(an)
names = family_names(an)
hier = an.pipeline.hierarchy.set_index("family_id")

st.write("Candidates are communities of **consumer-adjusted** co-purchase pairs. Approval records a research decision; taxonomy changes remain an explicit edit to the configuration.")
c = an.candidates
if c.empty:
    st.info("No candidate survived the thresholds.")
else:
    show_df(c.assign(families=c["families"].map(lambda fs: ", ".join(names.get(f, f) for f in fs)),
                     functions=c["functions"].map(", ".join), credibility_factors=c["credibility_factors"].map(
                         lambda d: " ".join(("[x]" if v else "[ ]") + k for k, v in d.items()))).round(3))
    pick = st.selectbox("Inspect candidate", list(c["candidate_id"]))
    row = c[c["candidate_id"] == pick].iloc[0]
    d = describe_candidate([names.get(f, f) for f in row["families"]], row["functions"])
    st.write(f"**{d['label']}** ({d['source']}): {d['description']}")
    if st.button("Send to review queue"):
        rq.add_item("candidate_need_state", {"candidate_id": pick, "families": row["families"], "description": d["description"],
                                              "factors": row["credibility_factors"]}, dedupe_key=f"{pick}:{'|'.join(row['families'])}")
        st.success("Queued.")

st.subheader("Entity-resolution near-duplicates")
rp = an.pipeline.resolution.review_pairs
if rp.empty:
    st.write("None.")
else:
    show_df(rp)

st.subheader("Review queue")
q = rq.list_items()
if q.empty:
    st.write("Queue is empty.")
else:
    show_df(q[["id", "kind", "status", "payload"]].astype({"payload": str}))
    pending = q[q["status"] == "pending"]
    if len(pending):
        item = st.selectbox("Decide on", list(pending["id"]))
        note = st.text_input("Note", "")
        cols = st.columns(3)
        for col, dec in zip(cols, ["approved", "rejected", "deferred"]):
            if col.button(dec.capitalize()):
                rq.decide(item, dec, note)
                st.rerun()
