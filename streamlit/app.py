from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_DIR = Path(os.environ.get("MASAR_PROJECT_DIR", "/app/project"))
INVENTORY_FILE = PROJECT_DIR / "data" / "processed" / "workbook_inventory.csv"

st.set_page_config(page_title="Masar", page_icon="🧭", layout="wide")
st.title("مسار | Masar")
st.caption("لوحة أولية لمتابعة مصادر البيانات")

source_files = sorted(PROJECT_DIR.glob("*.xlsx"))
left, right = st.columns(2)
left.metric("ملفات Excel", len(source_files))

if INVENTORY_FILE.exists():
    inventory = pd.read_csv(INVENTORY_FILE)
    right.metric("أوراق العمل", len(inventory))
    st.subheader("ملخص الملفات")
    st.dataframe(inventory, use_container_width=True, hide_index=True)
else:
    right.metric("أوراق العمل", "—")
    st.info("شغّل DAG باسم masar_core_pipeline من Airflow لإنتاج الملخص.")
    st.subheader("الملفات المكتشفة")
    st.dataframe(
        pd.DataFrame({"file_name": [path.name for path in source_files]}),
        use_container_width=True,
        hide_index=True,
    )

