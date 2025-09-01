# Import python packages
import streamlit as st
import requests  # needed for the API calls
import pandas as pd  # ← NEW: Bring in Pandas

st.title(f":cup_with_straw: Customize your smoothie :cup_with_straw: {st.__version__}")
st.write("Choose the fruits you want in your custom Smoothie!")

# Text input for customer name
name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your Smoothie will be", name_on_order)

# Connect using Streamlit secrets: [connections.snowflake]
cnx = st.connection("snowflake")

# ── Get fruit options + API search key (SEARCH_ON) ──────────────────────────────
# (Preserves your list of display names, adds a lookup for API calls)
fruit_df = cnx.query(
    """
    SELECT
        FRUIT_NAME,
        COALESCE(SEARCH_ON, FRUIT_NAME) AS SEARCH_ON
    FROM SMOOTHIES.PUBLIC.FRUIT_OPTIONS
    ORDER BY FRUIT_NAME
    """
)

# --- Challenge checkpoint (from previous step) ---------------------------------
# st.subheader("Fruit options with SEARCH_ON")
# st.dataframe(fruit_df[["FRUIT_NAME", "SEARCH_ON"]], use_container_width=True)
# st.stop()  # ← comment/remove to continue with the app

# Defensive trims (helpful if any values have stray spaces)
fruit_df["FRUIT_NAME"] = fruit_df["FRUIT_NAME"].str.strip()
fruit_df["SEARCH_ON"] = fruit_df["SEARCH_ON"].astype(str).str.strip()

fruit_options = fruit_df["FRUIT_NAME"].tolist()                 # what users see/choose
search_lookup = dict(zip(fruit_df["FRUIT_NAME"],                # UI name → API key
                         fruit_df["SEARCH_ON"]))

# Multiselect with limit (unchanged)
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    fruit_options,
    max_selections=5,
    placeholder="Pick up to 5 fruits…",
)
st.caption(f"{len(ingredients_list)}/5 selected")

# ── Bring in Pandas: fetch ALL selected fruits, show ONE consolidated table -----
if ingredients_list:
    rows = []
    for fruit_chosen in ingredients_list:
        api_key = search_lookup.get(fruit_chosen, fruit_chosen)
        try:
            resp = requests.get(
                f"https://my.smoothiefroot.com/api/fruit/{api_key}",
                timeout=10,
            )
            if resp.status_code == 200:
                payload = resp.json()
                nutr = payload.get("nutrition", {}) or {}
                # Build one tidy row per fruit
                rows.append({
                    "Fruit": fruit_chosen,                     # friendly display name
                    "API_Name": payload.get("name"),           # what the API calls it
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
                # Keep a row so the user knows which one failed to match
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

    # Render a single consolidated Pandas DataFrame
    if rows:
        df = pd.DataFrame(rows)
        # Optional: nicer order & index
        cols = ["Fruit", "API_Name", "Carbs", "Fat", "Protein", "Sugar", "Family", "Genus", "Order", "ID"]
        df = df[cols].set_index("Fruit")
        st.subheader("Selected Fruits — Nutrition Snapshot")
        st.dataframe(df, use_container_width=True)

# ── Insert the order when the button is clicked (preserved) ─────────────────────
if ingredients_list and name_on_order:
    ingredients_string = " ".join(ingredients_list)

    time_to_insert = st.button("Submit Order")
    if time_to_insert:
        # Write path uses Snowpark Session
        session = cnx.session()
        session.sql(
            """
            INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                (INGREDIENTS, NAME_ON_ORDER, ORDER_FILLED)
            VALUES (?, ?, FALSE)
            """,
            params=[ingredients_string, name_on_order],
        ).collect()

        st.success(f"Your Smoothie is ordered, {name_on_order}!", icon="✅")
