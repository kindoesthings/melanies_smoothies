# Import python packages
import streamlit as st
import requests  # already added earlier

st.title(f":cup_with_straw: Customize your smoothie :cup_with_straw: {st.__version__}")
st.write("Choose the fruits you want in your custom Smoothie!")

# Text input for customer name
name_on_order = st.text_input('Name on Smoothie:')
st.write("The name on your Smoothie will be", name_on_order)

# Connect using Streamlit secrets: [connections.snowflake]
cnx = st.connection("snowflake")

# --- CHANGED: pull both FRUIT_NAME and SEARCH_ON (fallback to FRUIT_NAME when NULL)
fruit_df = cnx.query("""
    SELECT
        FRUIT_NAME,
        COALESCE(SEARCH_ON, FRUIT_NAME) AS SEARCH_ON
    FROM SMOOTHIES.PUBLIC.FRUIT_OPTIONS
    ORDER BY FRUIT_NAME
""")

# list for the widget (what users see)
fruit_options = fruit_df["FRUIT_NAME"].tolist()
# lookup dict: display name -> API key
search_lookup = dict(zip(fruit_df["FRUIT_NAME"], fruit_df["SEARCH_ON"]))

# Multiselect with limit
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    fruit_options,
    max_selections=5,
    placeholder="Pick up to 5 fruits…"
)
st.caption(f"{len(ingredients_list)}/5 selected")

# Show nutrition panels for each chosen fruit using SEARCH_ON
if ingredients_list:
    for fruit_chosen in ingredients_list:
        api_key = search_lookup.get(fruit_chosen, fruit_chosen)  # fallback safety
        # If your SEARCH_ON is already normalized, no need to change case/spaces here
        resp = requests.get(
            f"https://my.smoothiefroot.com/api/fruit/{api_key}",
            timeout=10
        )
        if resp.ok:
            st.subheader(f"{fruit_chosen} Nutrition Information")
            st.dataframe(resp.json(), use_container_width=True)
        else:
            st.info(f"{fruit_chosen}: not found in the API (HTTP {resp.status_code}).")

# Only proceed if ingredients are chosen and name present
if ingredients_list and name_on_order:
    # Build a single string to match the lab's expected format (use display names)
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
