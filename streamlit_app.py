# Import python packages
import streamlit as st
import requests 

st.title(f":cup_with_straw: Customize your smoothie :cup_with_straw: {st.__version__}")
st.write("Choose the fruits you want in your custom Smoothie!")

# Text input for customer name
name_on_order = st.text_input('Name on Smoothie:')
st.write("The name on your Smoothie will be", name_on_order)

# Connect using Streamlit secrets: [connections.snowflake]
cnx = st.connection("snowflake")

# Get fruit options via SQL (read path uses .query)
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

# ── NEW: preview SmoothieFroot nutrition (watermelon placeholder)
# For this step of the lab we intentionally fetch "watermelon" for each selected item,
# so you should see the watermelon row repeated once per chosen ingredient.
if ingredients_list:
    preview_rows = []
    for fruit_chosen in ingredients_list:
        resp = requests.get("https://my.smoothiefroot.com/api/fruit/watermelon", timeout=10)
        preview_rows.append(resp.json())
    st.dataframe(preview_rows, use_container_width=True)

# Only proceed if ingredients are chosen and name present
if ingredients_list and name_on_order:
    # Build a single string to match the lab's expected format
    ingredients_string = " ".join(ingredients_list)

    # Button to submit order (prevents duplicate inserts on reruns)
    time_to_insert = st.button("Submit Order")

    if time_to_insert:
        # Use a Snowpark Session for DML (write path)
        session = cnx.session()  # requires snowflake-snowpark-python to be installed

        # Parameterized insert, explicitly setting ORDER_FILLED = FALSE
        session.sql(
            """
            INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                (INGREDIENTS, NAME_ON_ORDER, ORDER_FILLED)
            VALUES (?, ?, FALSE)
            """,
            params=[ingredients_string, name_on_order],
        ).collect()

        st.success(f"Your Smoothie is ordered, {name_on_order}!", icon="✅")
