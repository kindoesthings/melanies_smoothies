# Import python packages
import streamlit as st
import pandas as pd          # for .loc/.iloc lookups on a pandas DataFrame
import requests              # for the nutrition API

st.title(f":cup_with_straw: Customize your smoothie :cup_with_straw: {st.__version__}")
st.write("Choose the fruits you want in your custom Smoothie!")

# ── Name on Order ───────────────────────────────────────────────────────────────
name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your Smoothie will be", name_on_order)

# ── Connect to Snowflake ────────────────────────────────────────────────────────
cnx = st.connection("snowflake")
session = cnx.session()  # Snowpark Session for reads + INSERT

# Read fruit options (Snowpark → pandas) including SEARCH_ON mapping
my_dataframe = (
    session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
           .select("FRUIT_NAME", "SEARCH_ON")
)
pd_df = my_dataframe.to_pandas()

# Clean up whitespace just in case
pd_df["FRUIT_NAME"] = pd_df["FRUIT_NAME"].astype(str).str.strip()
pd_df["SEARCH_ON"]  = pd_df["SEARCH_ON"].astype(str).str.strip()

# Options shown in the multiselect
fruit_options = pd_df["FRUIT_NAME"].tolist()

# ── Pick up to 5 ingredients ───────────────────────────────────────────────────
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    fruit_options,
    max_selections=5,
    placeholder="Pick up to 5 fruits…",
)
st.caption(f"{len(ingredients_list)}/5 selected")

# ── Build ingredients string for the order (used later on submit) ──────────────
ingredients_string = " ".join(ingredients_list) if ingredients_list else ""

# ── Nutrition info for each chosen fruit (uses SEARCH_ON mapping) ──────────────
for fruit_chosen in ingredients_list:
    # Find API search key for this fruit; fall back to the display name
    match = pd_df.loc[pd_df["FRUIT_NAME"] == fruit_chosen, "SEARCH_ON"]
    search_on = match.iloc[0] if not match.empty and pd.notna(match.iloc[0]) else fruit_chosen

    st.subheader(f"{fruit_chosen} Nutrition Information")
    try:
        # SmoothieFroot API
        resp = requests.get(
            f"https://my.smoothiefroot.com/api/fruit/{search_on}",
            timeout=10,
        )
        if resp.status_code == 200:
            st.dataframe(resp.json(), use_container_width=True)
        elif resp.status_code == 404:
            st.info(f"{fruit_chosen}: not found in the API (HTTP 404).")
        else:
            st.warning(f"{fruit_chosen}: API returned HTTP {resp.status_code}.")
    except requests.RequestException as e:
        st.error(f"Error contacting nutrition API for {fruit_chosen}: {e}")

# ── Submit button BELOW the nutrition tables ───────────────────────────────────
# Show it only when we have both a name and at least one ingredient.
if name_on_order and ingredients_list:
    # Place the button AFTER the tables so it appears at the bottom like the screenshot
    submit_clicked = st.button("Submit Order")

    if submit_clicked and not st.session_state.get("order_just_submitted"):
        # Insert into ORDERS and mark as not yet filled
        session.sql(
            """
            INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                (INGREDIENTS, NAME_ON_ORDER, ORDER_FILLED)
            VALUES (?, ?, FALSE)
            """,
            params=[ingredients_string, name_on_order],
        ).collect()

        st.session_state["order_just_submitted"] = True  # avoid accidental double-submits
        st.success(f"Your Smoothie is ordered, {name_on_order}!", icon="✅")
