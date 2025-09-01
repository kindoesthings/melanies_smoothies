# Import python packages
import streamlit as st
import pandas as pd
import requests

# App header
st.title(f":cup_with_straw: Customize your smoothie :cup_with_straw: {st.__version__}")
st.write("Choose the fruits you want in your custom Smoothie!")

# Text input for customer name
name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your Smoothie will be", name_on_order)

# Connect using Streamlit secrets: [connections.snowflake]
cnx = st.connection("snowflake")

# ── Read fruit options + SEARCH_ON from Snowflake ───────────────────────────────
# We build a pandas DataFrame (pd_df) so we can use loc/iloc like in the lab.
fruit_df = cnx.query(
    """
    SELECT
        FRUIT_NAME,
        COALESCE(SEARCH_ON, FRUIT_NAME) AS SEARCH_ON
    FROM SMOOTHIES.PUBLIC.FRUIT_OPTIONS
    ORDER BY FRUIT_NAME
    """
)
pd_df = fruit_df.copy()  # "Make a version of my_dataframe, but call it pd_df"

# (Lab debug step — uncomment when asked)
# st.dataframe(pd_df, use_container_width=True)
# st.stop()

# Options shown to the user come from FRUIT_NAME
fruit_options = pd_df["FRUIT_NAME"].tolist()

# ── Multiselect with limit ───────────────────────────────────────────────────────
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    fruit_options,
    max_selections=5,
    placeholder="Pick up to 5 fruits…",
)
st.caption(f"{len(ingredients_list)}/5 selected")

# ── Insert the order when the button is clicked ─────────────────────────────────
if ingredients_list and name_on_order:
    ingredients_string = " ".join(ingredients_list)
    time_to_insert = st.button("Submit Order")
    if time_to_insert:
        # Use Snowpark Session for DML
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

# ── Make use of the SEARCH_ON value when calling the API ────────────────────────
# For each selected fruit, look up the API key via pd_df.loc[...] and call the API.
for fruit_chosen in ingredients_list:
    # Get the API search key that corresponds to the UI label
    match = pd_df.loc[pd_df["FRUIT_NAME"] == fruit_chosen, "SEARCH_ON"]
    search_on = match.iloc[0] if not match.empty else fruit_chosen  # safe fallback

    # (Optional lab debug line)
    # st.write("The search value for ", fruit_chosen, " is ", search_on, ".")

    st.subheader(f"{fruit_chosen} Nutrition Information")
    try:
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
