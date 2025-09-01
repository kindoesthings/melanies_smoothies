# Import python packages
import streamlit as st
import requests  # NEW: needed for the API calls
import pandas as pd 

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

# --- Challenge checkpoint: preview the dataframe feeding the multiselect -----
#st.subheader("Fruit options with SEARCH_ON")
#st.dataframe(fruit_df[["FRUIT_NAME", "SEARCH_ON"]], use_container_width=True)
#st.stop()  # ← remove or comment this after you verify the table

#convert
pd_df = my_dataframe.to_pandas()
st.dataframe(pd_df)
st.stop()

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

# ── Show nutrition info for each selected fruit (NEW) ───────────────────────────
# Uses SEARCH_ON so 'Blueberries' → 'Blueberry', etc. 404s are shown as info.
for fruit_chosen in ingredients_list:
    api_key = search_lookup.get(fruit_chosen, fruit_chosen)
    st.subheader(f"{fruit_chosen} Nutrition Information")
    try:
        resp = requests.get(
            f"https://my.smoothiefroot.com/api/fruit/{api_key}",
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

# (Removed the old single-watermelon test call to the API)
