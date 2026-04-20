import streamlit as st

st.title("Streamlit App")
st.header("Welcome")
st.write("This is a Basic streamlit app.")

name = st.text_input("Enter Your Name:")
if name:
    st.success(f"Hello,{name}! \nHow are you?")

number = st.slider("Pick you age", 0, 100)
st.write(f"Your age is {number}")
