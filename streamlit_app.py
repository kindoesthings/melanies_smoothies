import streamlit as st

cnx = st.connection("snowflake")

fruit_df = cnx.query("select FRUIT_NAME from SMOOTHIES.PUBLIC.FRUIT_OPTIONS order by 1")
fruit_options = fruit_df["FRUIT_NAME"].tolist()

ingredients = st.multiselect("Choose up to 5 ingredients:", fruit_options, max_selections=5)

name_on_order = st.text_input("Name on Smoothie:")

if ingredients and name_on_order and st.button("Submit Order"):
    cnx.query(
        "insert into SMOOTHIES.PUBLIC.ORDERS(INGREDIENTS, NAME_ON_ORDER) values (%s, %s)",
        params=(" ".join(ingredients), name_on_order),
    )
    st.success(f"Your Smoothie is ordered, {name_on_order}!", icon="✅")
