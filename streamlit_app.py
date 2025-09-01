# Import python packages
import streamlit as st
import pandas as pd
import requests

st.title(f":cup_with_straw: Customize your smoothie :cup_with_straw: {st.__version__}")
st.write("Choose the fruits you want in your custom Smoothie!")

# --- Name input ---------------------------------------------------------------
name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your Smoothie will be", name_on_order)

# --- Connect to Snowflake -----------------------------------------------------
cnx = st.connection("snowflake")
session = cnx.session()  # write path & Snowpark table access

# --- Pull fruit list (FRUIT_NAME + SEARCH_ON) and make a Pandas DataFrame -----
my_dataframe = (
    session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
    .select("FRUIT_NAME", "SEARCH_ON")
)

pd_df = my_dataframe.to_pandas()  # convert Snowpark DataFrame -> Pandas

# Clean up values and backfill SEARCH_ON when null
pd_df["FRUIT_NAME"] = pd_df["FRUIT_NAME"].astype(str).str.strip()
pd_df["SEARCH_ON"]  = (
    pd_df["SEARCH_ON"].where(pd.notna(pd_df["SEARCH_ON"]), pd_df["FRUIT_NAME"])
    .astype(str)
    .str.strip()
)

# OPTIONAL: quick debug peek, like in the lab steps
with st.expander("🔎 Debug: show source dataframe (FRUIT_NAME + SEARCH_ON)"):
    st.dataframe(pd_df, use_container_width=True)
    st.caption("Close this expander to continue.")

# --- Multiselect (limit 5) ----------------------------------------------------
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    pd_df["FRUIT_NAME"].tolist(),
    max_selections=5,
    placeholder="Pick up to 5 fruits…",
)
st.caption(f"{len(ingredients_list)}/5 selected")

# --- Insert order when user clicks Submit ------------------------------------
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

# --- Nutrition info for each selected fruit (uses the 'strange-looking' loc) --
for fruit_chosen in ingredients_list:
    # This is the “strange-looking” line from the lab:
    match = pd_df.loc[pd_df["FRUIT_NAME"] == fruit_chosen, "SEARCH_ON"]
    search_on = match.iloc[0] if not match.empty else fruit_chosen  # safe fallback

    # Echo the mapping (as in the screenshot)
    st.write("The search value for ", fruit_chosen, " is ", search_on, ".")

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
