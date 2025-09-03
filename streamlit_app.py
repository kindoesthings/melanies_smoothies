# Import python packages
import streamlit as st
import snowflake.snowpark.functions import col
import pandas as pd          
import requests              

st.title(f":cup_with_straw: Customize your smoothie :cup_with_straw: {st.__version__}")
st.write("Choose the fruits you want in your custom Smoothie!")

name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your Smoothie will be", name_on_order)

cnx = st.connection("snowflake")
session = cnx.session() 

my_dataframe = (
    session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
           .select("FRUIT_NAME", "SEARCH_ON")
)
pd_df = my_dataframe.to_pandas()

pd_df["FRUIT_NAME"] = pd_df["FRUIT_NAME"].astype(str).str.strip()
pd_df["SEARCH_ON"]  = pd_df["SEARCH_ON"].astype(str).str.strip()

fruit_options = pd_df["FRUIT_NAME"].tolist()

ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    fruit_options,
    max_selections=5,
    placeholder="Pick up to 5 fruits…",
)
st.caption(f"{len(ingredients_list)}/5 selected")

ingredients_string = " ".join(ingredients_list) if ingredients_list else ""

for fruit_chosen in ingredients_list:
    # Find API search key for this fruit; fall back to the display name
    match = pd_df.loc[pd_df["FRUIT_NAME"] == fruit_chosen, "SEARCH_ON"]
    search_on = match.iloc[0] if not match.empty and pd.notna(match.iloc[0]) else fruit_chosen

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
