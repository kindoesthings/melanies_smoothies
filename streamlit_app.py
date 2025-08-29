# Import python packages
import streamlit as st
from snowflake.snowpark.functions import col  # requires snowflake-snowpark-python

st.title(f":cup_with_straw: Customize your smoothie :cup_with_straw: {st.__version__}")
st.write("Choose the fruits you want in your custom Smoothie!")

name_on_order = st.text_input('Name on Smoothie:')
st.write("The name on your Smoothie will be", name_on_order)

# Connect using Streamlit connections (reads secrets at [connections.snowflake])
cnx = st.connection("snowflake")
session = cnx.session()                      # Snowpark Session

# Get options -> convert to list
fruit_sp = session.table("smoothies.public.fruit_options").select(col('FRUIT_NAME'))
fruit_options = fruit_sp.to_pandas()['FRUIT_NAME'].tolist()   # or [r[0] for r in fruit_sp.collect()]

# Multiselect (limit to 5)
ingredients_list = st.multiselect(
    'Choose up to 5 ingredients:',
    fruit_options,
    max_selections=5,
    placeholder="Pick up to 5 fruits…"
)
st.caption(f"{len(ingredients_list)}/5 selected")

if ingredients_list and name_on_order:
    ingredients_string = ' '.join(ingredients_list)

    # Safer, parameterized insert
    session.sql(
        "insert into smoothies.public.orders(ingredients, name_on_order) values (?, ?)",
        params=[ingredients_string, name_on_order]
    ).collect()

    st.success(f"Your Smoothie is ordered, {name_on_order}!", icon="✅")
