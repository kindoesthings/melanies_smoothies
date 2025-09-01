# Import python packages
import streamlit as st
import requests
import pandas as pd
from snowflake.snowpark.functions import col  # NEW: for the Snowpark select()

st.title(f":cup_with_straw: Customize your smoothie :cup_with_straw: {st.__version__}")
st.write("Choose the fruits you want in your custom Smoothie!")

# Text input for customer name
name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your Smoothie will be", name_on_order)

# Connect using Streamlit secrets: [connections.snowflake]
cnx = st.connection("snowflake")

# ── Snowpark DF -> Pandas DF for the multiselect (this lesson step) ─────────────
session = cnx.session()

# 1) Snowpark dataframe with the two needed columns
my_dataframe = (
    session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
    .select(col("FRUIT_NAME"), col("SEARCH_ON"))
)

# (optional peek) show the Snowpark DF
# st.subheader("Snowpark my_dataframe")
# st.dataframe(data=my_dataframe, use_container_width=True)
# st.stop()

# 2) Convert to Pandas
pd_df = my_dataframe.to_pandas()

# ✅ Checkpoint for the lab step — leave these two lines ON to verify this part.
st.subheader("Pandas pd_df (FRUIT_NAME + SEARCH_ON)")
st.dataframe(pd_df, use_container_width=True)
st.stop()  # ← comment this out after you’ve confirmed the preview looks right

# ── From here on, use pd_df just like your old fruit_df ─────────────────────────
# Clean up whitespace / types
pd_df["FRUIT_NAME"] = pd_df["FRUIT_NAME"].astype(str).str.strip()
pd_df["SEARCH_ON"] = pd_df["SEARCH_ON"].astype(str).str.strip()

fruit_options = pd_df["FRUIT_NAME"].tolist()  # what users see/choose
search_lookup = dict(zip(pd_df["FRUIT_NAME"], pd_df["SEARCH_ON"]))  # UI → API key

# Multiselect with limit
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    fruit_options,
    max_selections=5,
    placeholder="Pick up to 5 fruits…",
)
st.caption(f"{len(ingredients_list)}/5 selected")

# ── Consolidated nutrition table (your recent “Bring in Pandas” step) ───────────
if ingredients_list:
    rows = []
    for fruit_chosen in ingredients_list:
        api_key = search_lookup.get(fruit_chosen, fruit_chosen)
        try:
            resp = requests.get(f"https://my.smoothiefroot.com/api/fruit/{api_key}", timeout=10)
            if resp.status_code == 200:
                payload = resp.json()
                nutr = payload.get("nutrition", {}) or {}
                rows.append({
                    "Fruit": fruit_chosen,
                    "API_Name": payload.get("name"),
                    "Carbs": nutr.get("carbs"),
                    "Fat": nutr.get("fat"),
                    "Protein": nutr.get("protein"),
                    "Sugar": nutr.get("sugar"),
                    "Family": payload.get("family"),
                    "Genus": payload.get("genus"),
                    "Order": payload.get("order"),
                    "ID": payload.get("id"),
                })
            elif resp.status_code == 404:
                rows.append({
                    "Fruit": fruit_chosen,
                    "API_Name": None,
                    "Carbs": None, "Fat": None, "Protein": None, "Sugar": None,
                    "Family": None, "Genus": None, "Order": None, "ID": None,
                })
            else:
                st.warning(f"{fruit_chosen}: API returned HTTP {resp.status_code}.")
        except requests.RequestException as e:
            st.error(f"Error contacting nutrition API for {fruit_chosen}: {e}")

    if rows:
        import pandas as pd
        df = pd.DataFrame(rows)
        cols = ["Fruit", "API_Name", "Carbs", "Fat", "Protein", "Sugar", "Family", "Genus", "Order", "ID"]
        st.subheader("Selected Fruits — Nutrition Snapshot")
        st.dataframe(df[cols].set_index("Fruit"), use_container_width=True)

# ── Insert the order when the button is clicked (unchanged) ─────────────────────
if ingredients_list and name_on_order:
    ingredients_string = " ".join(ingredients_list)
    time_to_insert = st.button("Submit Order")
    if time_to_insert:
        session.sql(
            """
            INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                (INGREDIENTS, NAME_ON_ORDER, ORDER_FILLED)
            VALUES (?, ?, FALSE)
            """,
            params=[ingredients_string, name_on_order],
        ).collect()
        st.success(f"Your Smoothie is ordered, {name_on_order}!", icon="✅")
