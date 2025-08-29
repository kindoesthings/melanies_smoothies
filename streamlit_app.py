# Import python packages
import streamlit as st

st.title(f":cup_with_straw: Customize your smoothie :cup_with_straw: {st.__version__}")
st.write("Choose the fruits you want in your custom Smoothie!")

# Text input for customer name
name_on_order = st.text_input('Name on Smoothie:')
st.write("The name on your Smoothie will be", name_on_order)

# Connect using Streamlit secrets: [connections.snowflake]
cnx = st.connection("snowflake")

# Get fruit options via SQL (no Snowpark import needed)
fruit_df = cnx.query("SELECT FRUIT_NAME FROM SMOOTHIES.PUBLIC.FRUIT_OPTIONS ORDER BY FRUIT_NAME")
fruit_options = fruit_df["FRUIT_NAME"].tolist()

# Multiselect with limit
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    fruit_options,
    max_selections=5,
    placeholder="Pick up to 5 fruits…"
)
st.caption(f"{len(ingredients_list)}/5 selected")

# Only proceed if ingredients are chosen and name present
if ingredients_list and name_on_order:
    ingredients_string = " ".join(ingredients_list)

    # Parameterized insert (safe)
    cnx.query(
        "INSERT INTO SMOOTHIES.PUBLIC.ORDERS(INGREDIENTS, NAME_ON_ORDER) VALUES (%s, %s)",
        params=(ingredients_string, name_on_order),
    )

    st.success(f"Your Smoothie is ordered, {name_on_order}!", icon="✅")
