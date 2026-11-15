from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from algorithms.aco import ACOConfig
from algorithms.route_optimizer import RouteOptimizer
from network.road_network import load_road_network
from traffic.traffic_simulator import TrafficSimulator
from traffic.tomtom_api import get_live_traffic
from utils.config import APP_NAME, DEFAULT_CITY
from visualization.charts import plot_cost_history, plot_route_comparison
from visualization.map_view import build_route_map


st.set_page_config(page_title=APP_NAME, page_icon="🚚", layout="wide")


def default_sample_stops() -> list[tuple[float, float]]:
    return [
        (27.1779, 78.0101),
        (27.1754, 78.0130),
        (27.1733, 78.0076),
        (27.1784, 78.0052),
    ]


if "city" not in st.session_state:
    st.session_state.city = DEFAULT_CITY
if "network" not in st.session_state:
    st.session_state.network = load_road_network(st.session_state.city, offline_only=True)
if "depot" not in st.session_state:
    st.session_state.depot = (27.1767, 78.0081)
if "stops" not in st.session_state:
    st.session_state.stops = default_sample_stops()
if "route_result" not in st.session_state:
    st.session_state.route_result = None
if "traffic_simulator" not in st.session_state:
    st.session_state.traffic_simulator = TrafficSimulator(seed=42)
if "traffic_mode" not in st.session_state:
    st.session_state.traffic_mode = "Simulation only"
if "route_history" not in st.session_state:
    st.session_state.route_history = []


with st.sidebar:
    st.header("RouteX")
    st.caption("Dynamic vehicle routing with ACO and traffic-aware replanning")
    page = st.radio(
        "Navigation",
        ["Overview", "Route Planning", "Live Traffic", "Dynamic Replanning", "Analytics", "About"],
        index=0,
    )
    st.markdown("---")
    st.subheader("City")
    st.session_state.city = st.text_input("Operating city", value=st.session_state.city)
    if st.button("Load city network"):
        st.session_state.network = load_road_network(st.session_state.city, offline_only=True)
        st.session_state.route_result = None
    st.session_state.traffic_mode = st.radio(
        "Traffic source",
        ["Both live traffic and simulation", "Simulation only", "Live traffic only"],
        index=0,
    )

    st.subheader("Vehicle")
    mileage = st.slider("Vehicle mileage (km/litre)", min_value=5.0, max_value=25.0, value=12.0, step=0.5)

    st.subheader("ACO settings")
    num_ants = st.slider("Number of ants", 5, 80, 20)
    alpha = st.slider("Alpha", 0.1, 3.0, 1.0, step=0.1)
    beta = st.slider("Beta", 0.5, 6.0, 3.0, step=0.1)
    evaporation = st.slider("Evaporation rate", 0.05, 0.5, 0.2, step=0.05)
    iterations = st.slider("Iterations", 10, 200, 40)


st.title("🚚 RouteX")
st.caption("Dynamic Vehicle Routing Using Ant Colony Optimization and Traffic Data")

if page == "Overview":
    st.info("The project combines real road networks, custom ACO optimization, and traffic-aware route replanning for a complete delivery-routing workflow.")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("City", st.session_state.city)
    with col2:
        st.metric("Stops", len(st.session_state.stops))
    with col3:
        st.metric("Traffic mode", st.session_state.traffic_mode)

    if st.session_state.route_result:
        metrics = st.session_state.route_result.metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Distance", f"{metrics.get('distance_km', 0.0):.2f} km")
        with col2:
            st.metric("Travel time", f"{metrics.get('travel_time_minutes', 0.0):.2f} min")
        with col3:
            st.metric("Fuel", f"{metrics.get('fuel_liters', 0.0):.2f} L")
    else:
        st.warning("No route has been optimized yet. Go to Route Planning to generate an initial route.")

elif page == "Route Planning":
    st.subheader("Route planning")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.depot = (
            st.number_input("Depot latitude", value=st.session_state.depot[0], format="%.6f"),
            st.number_input("Depot longitude", value=st.session_state.depot[1], format="%.6f"),
        )
    with col2:
        st.write("Sample stop coordinates")
        sample_df = pd.DataFrame({"latitude": [lat for lat, _ in st.session_state.stops], "longitude": [lon for _, lon in st.session_state.stops]})
        st.dataframe(sample_df, use_container_width=True)

    if st.button("Run optimization"):
        config = ACOConfig(
            num_ants=int(num_ants),
            alpha=float(alpha),
            beta=float(beta),
            evaporation_rate=float(evaporation),
            iterations=int(iterations),
            random_seed=42,
        )
        optimizer = RouteOptimizer(st.session_state.network, st.session_state.depot, st.session_state.stops, config=config)
        result = optimizer.optimize(mileage_km_per_litre=float(mileage))
        st.session_state.route_result = result
        st.session_state.route_history = result.history
        st.success(f"Optimization complete: {result.metrics.get('distance_km', 0.0):.2f} km, {result.metrics.get('travel_time_minutes', 0.0):.2f} min.")

    if st.session_state.route_result:
        route = st.session_state.route_result.route
        map_obj = build_route_map(st.session_state.network, depot=st.session_state.depot, stops=st.session_state.stops, route=route)
        st.components.v1.html(map_obj.get_root().render(), height=500)

        stats = st.session_state.route_result.metrics
        st.subheader("Route metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Distance", f"{stats.get('distance_km', 0.0):.2f} km")
        with col2:
            st.metric("Travel time", f"{stats.get('travel_time_minutes', 0.0):.2f} min")
        with col3:
            st.metric("Fuel", f"{stats.get('fuel_liters', 0.0):.2f} L")

elif page == "Live Traffic":
    st.subheader("Traffic status")
    status = get_live_traffic(st.session_state.city, st.session_state.depot[0], st.session_state.depot[1])
    st.write(status.get("message", "Traffic status unavailable."))
    if status.get("available"):
        st.success("Live traffic is available and is being used where possible.")
    else:
        st.warning("Live traffic is unavailable. Simulation mode is active as a fallback.")

    st.markdown("### Congestion controls")
    traffic_level = st.selectbox("Traffic level", ["normal", "moderate", "heavy", "severe"], index=1)
    if st.button("Apply simulation congestion"):
        st.session_state.traffic_simulator.apply_random_congestion(st.session_state.network, level=traffic_level, fraction=0.25)
        st.session_state.traffic_simulator.update_all_travel_times(st.session_state.network)
        st.success(f"Traffic simulation updated to {traffic_level} level.")

elif page == "Dynamic Replanning":
    st.subheader("Dynamic replanning")
    if not st.session_state.route_result:
        st.warning("Optimize a route before testing dynamic replanning.")
    else:
        delivered = st.multiselect(
            "Completed deliveries",
            options=list(range(len(st.session_state.stops))),
            default=[],
        )
        if st.button("Trigger replanning"):
            optimizer = RouteOptimizer(st.session_state.network, st.session_state.depot, st.session_state.stops, config=ACOConfig(random_seed=42))
            update = optimizer.replan_remaining(delivered)
            st.session_state.route_history.append(update.metrics)
            st.success(f"Replanning complete for {len(delivered)} completed deliveries.")
            st.json(update.metrics)

elif page == "Analytics":
    st.subheader("Optimization analytics")
    if st.session_state.route_result:
        figure = plot_cost_history(st.session_state.route_result.history)
        st.pyplot(figure)
        st.caption("Best ACO objective value per iteration")
    else:
        st.info("No optimization history yet.")

elif page == "About":
    st.markdown(
        """
        ## RouteX

        RouteX solves a dynamic vehicle routing problem using a custom ant colony optimizer.
        The algorithm optimizes the delivery sequence while actual road-network paths are computed
        with NetworkX and OSMnx. Traffic conditions can be simulated or supplied by a live API,
        and the optimizer can replan only the remaining deliveries after traffic changes.

        ### Core ideas
        - Vehicle Routing Problem (VRP): find a low-cost route through delivery stops.
        - Ant Colony Optimization (ACO): pheromone trails guide ants toward good sequences.
        - Multi-objective cost: normalized distance, time and fuel are blended into a single score.
        - Dynamic routing: traffic updates trigger replanning while preserving completed deliveries.
        """
    )

st.markdown("---")
if os.getenv("TOMTOM_API_KEY"):
    st.caption("Live traffic API is configured.")
else:
    st.caption("Simulation mode is active. Add TOMTOM_API_KEY to enable live traffic.")
