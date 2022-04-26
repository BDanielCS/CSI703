import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import plotly.express as px

# SETTING PAGE CONFIG TO WIDE MODE
st.set_page_config(layout="wide")

# LOAD DATA ONCE
@st.experimental_singleton
def load_data():
	# Load in the taxi data from above (only a sample of the rows though)
	taxi_trips = pd.read_csv("data/taxi_sample.csv").dropna(subset=["Pickup_Centroid_Longitude","Pickup_Centroid_Latitude"])
	diabetes_df = pd.read_csv("CDC_Diabetes/diabetes_binary_health_indicators_BRFSS2015.csv")
	return taxi_trips, diabetes_df


# # FUNCTION FOR AIRPORT MAPS
def map(data, lat, lon, zoom):
	data['lat'] = pd.to_numeric(data["Pickup_Centroid_Latitude"])
	data['lon'] = pd.to_numeric(data["Pickup_Centroid_Longitude"])
	st.map(data, zoom=zoom)


# Filter taxi trip data by length of trip
@st.experimental_memo
def filter_by_trip_distance(df, length_of_trip):
	return df[df["Trip Miles"].between(length_of_trip - 1, length_of_trip)].copy()


# Clean up Diabetic income and tune number of bins
@st.experimental_memo
def diabetic_salary_prep(diabetes_df, diab_status):
	# From the CDC survey, map each numeric category to the human readable string as a dictionary
	income_code_to_text = {
		1: "Less than $10,000",
		2: "$10,000 - $15,000",
		3: "$15,000 - $20,000",
		4: "$20,000 - $25,000",
		5: "$25,000 - $35,000",
		6: "$35,000 - $50,000",
		7: "$50,000 - $75,000",
		8: "$75,000 or more",
		77: "Don’t know/Not sure",
		99:"Refused"
	}

	diabetes_df['Has Diabetes'] = diabetes_df['Diabetes_binary'].astype(bool)
	if diab_status == "True":
		diabetes_applicable = diabetes_df[diabetes_df['Has Diabetes']].copy()
	else:
		diabetes_applicable = diabetes_df[~diabetes_df['Has Diabetes']].copy()

	# Start counting the number of diabetics or non-diabetics at each income
	diabetes_counts = diabetes_applicable[['Income', 'Has Diabetes']].groupby(["Income","Has Diabetes"]).size().reset_index()
	diabetes_counts.columns = ["Income", "Has Diabetes", "Number of Individuals"]
	diabetes_counts['Income Bracket'] = diabetes_counts['Income'].apply(lambda x : income_code_to_text[x])
	return diabetes_counts

# Prepare the diabetes dataframe to be used for BMI exploratory analysis
def diabetic_bmi_prep(diabetes_df):
	diabetes_df['Has Diabetes Bin'] = diabetes_df['Diabetes_binary'].astype(bool)
	diabetes_df['Diabetic Status'] = diabetes_df['Has Diabetes Bin'].apply(lambda x : "Diabetic" if x else "Non-Diabetic")
	return diabetes_df

# Prepare the diabetes dataframe for a inspection of the qualitative fields
def gen_health_prep(qualitative_data, diab_status):
	# Map each of the columns to human readable text - FOCUS ON GenHlth and Diabetic status
	gen_hlth_mapping = {
	    1: "Excellent",
	    2: "Very Good",
	    3: "Good",
	    4: "Fair",
	    5: "Poor",
	    7: "Don't know / Not Sure",
	    9: "Refused",
	}

	qualitative_data['Has Diabetes'] = qualitative_data['Diabetes_binary'].astype(bool)
	qualitative_data['General_Health_Assessment'] = qualitative_data['GenHlth'].apply(lambda x : gen_hlth_mapping[int(x)])
	qualitative_data['has_diabetes_human_readable'] = qualitative_data['Diabetes_binary'].apply(lambda x : "Diabetic" if x == 1 else "Non-Diabetic")

	if diab_status == "True":
		applicable_qual_data = qualitative_data[qualitative_data['Has Diabetes']].copy()
	else:
		applicable_qual_data = qualitative_data[~qualitative_data['Has Diabetes']].copy()
	return applicable_qual_data



# ##############################################################################################################
# # Begin Main Logic 
# ##############################################################################################################

# STREAMLIT load our csvs
taxis, diabetes = load_data()

##################################################
# Geospatial Visualizations
##################################################
column_1, column_2 = st.columns((2, 2))

with column_1:
	st.title("Geospatial Visualization")
	length_of_trip = st.slider("Select Trip Length (Miles)", value = 10, min_value=1, max_value=25)


# Prepare the map
row2_1, row2_2 = st.columns((2,2))
zoom_level = 9
taxi_midpoint = [41.9, -87.2] # Let's use this as our midpoint

with row2_1:
	st.write(
		f"""Taxi pickup locations where the taxi traveled {length_of_trip} miles."""
	)
	map(filter_by_trip_distance(taxis, length_of_trip), taxi_midpoint[0], taxi_midpoint[1], zoom_level)

with row2_2:
	st.write("""
##
	Let's take a look at Chicago taxi pickup locations from July 2016 and how
	far their trips were. Use the slider bar to filter the data based on some 
	maximum trip distance (in miles). 

		""")


##################################################
# Visualizing Distributions & Part to Whole
##################################################
p2_column_1, p2_column_2 = st.columns((2, 2))

with p2_column_1:
	st.title("Visualizing Distributions & Part to Whole")
	diabetes_status = st.radio(
		label="Has Diabetes",
		options=('True', 'False'),
		index=0
	)

p2_row2_1, p2_row2_2 = st.columns((2,2))
with p2_row2_1:
	filtered_diabetes = diabetic_salary_prep(diabetes, diabetes_status)[["Income Bracket", "Number of Individuals"]]
	c = alt.Chart(filtered_diabetes).mark_bar().encode(
	    x='Income Bracket',
	    y='Number of Individuals'
	)

	st.altair_chart(c, use_container_width=True)


with p2_row2_2:
	st.write("""
		Let's see how the distribution of income with diabetes versus without diabetes
		compares and get some practice using a radio button too.

	""")


##################################################
# Visualizing correlation, comparisons, and trends.
##################################################
p3_column_1, _ = st.columns((2, 2))

with p3_column_1:
	st.title("Visualizing correlation, comparisons, and trends")
	max_bmi = st.number_input('Maximum BMI to observe (1-100)', value=100, min_value=1, max_value=100)

p3_row2_1, p3_row2_2 = st.columns((2,2))
with p3_row2_1:
	prepared_diabetes = diabetic_bmi_prep(diabetes)
	prepared_diabetes = prepared_diabetes[prepared_diabetes['BMI'] <= max_bmi]
	bmi_c = alt.Chart(prepared_diabetes).transform_density(
		'BMI',
		as_=['BMI', 'density'],
    	extent=[0, max_bmi],
		groupby=['Diabetic Status']
	).mark_area(orient='horizontal').encode(
	    y='BMI:Q',
	    color='Diabetic Status:N',
	    x=alt.X(
	        'density:Q',
	        stack='center',
	        impute=None,
	        title=None,
	        axis=alt.Axis(labels=False, values=[0],grid=False, ticks=True),
    	)
    )
	st.altair_chart(bmi_c)


with p3_row2_2:
	st.write("""
		Let's see how the distribution of BMI compares with respect to those with diabetes
		versus those without diabetes
	""")


##################################################
# Visualizing correlation, comparisons, and trends.
##################################################
p4_column_1, _ = st.columns((2, 2))

with p4_column_1:
	st.title("Visualizing concepts and qualitative data")
	diabetes_status_tree = st.selectbox(
		label="Has Diabetes",
		options=('True', 'False'),
		index=0
	)

p4_row2_1, p4_row2_2 = st.columns((2,2))

with p4_row2_1:
	applicable_gen_health = gen_health_prep(diabetes, diabetes_status_tree)

	fig = px.treemap(applicable_gen_health, path=[px.Constant("all"), 'has_diabetes_human_readable', 'General_Health_Assessment'],
                title="Frequency of General Health Qualitative Measurements by Diabetic Status")
	fig.update_traces(root_color="lightgray")
	fig.update_layout(margin = dict(t=50, l=25, r=25, b=25))
	st.plotly_chart(fig, use_container_width=True)

with p4_row2_2:
	st.write("""
		Let's see how the use of the qualitative "general health" phrases from the
		diabetes survey data change depending on whether you are a diabetic versus
		non-diabetes. Also use this as an opportunity for a select box
	""")

