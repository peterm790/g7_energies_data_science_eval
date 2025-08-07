from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import os
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import time
import seaborn as sns

def setup_driver(download_dir):
    """
    Configure and initialize Chrome WebDriver for downloading charts.
    
    Args:
        download_dir (str): Directory path for saving downloaded files
        
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
    """
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option('prefs', prefs)
    return webdriver.Chrome(options=chrome_options)

def get_latest_file(directory, before=None):
    """
    Get the most recently downloaded SVG file from directory.
    
    Args:
        directory (str): Directory to search for SVG files
        before (float, optional): Timestamp to compare against
        
    Returns:
        str: Filename of latest SVG file, or None if not found
    """
    files = [(f, os.path.getctime(os.path.join(directory, f))) 
             for f in os.listdir(directory) if f.endswith('.svg')]
    if not files:
        return None
    newest_file = max(files, key=lambda x: x[1])
    if before and newest_file[1] < before:
        return None
    return newest_file[0]

def download_chart(commodity='lithium'):
    """
    Download price chart from Trading Economics website.
    
    Args:
        commodity (str): Name of commodity to download
        
    Returns:
        str: Path to downloaded SVG file, or None if download failed
    """
    download_dir = os.getcwd()
    driver = setup_driver(download_dir)
    
    try:
        before_download = time.time()
        driver.get(f"https://tradingeconomics.com/commodity/{commodity}")
        wait = WebDriverWait(driver, 10)
        actions = ActionChains(driver)
        
        buttons = [
            (By.CSS_SELECTOR, "#trading_chart > div > div.iChart-wrapper-footer > div.iChart-menu2-bottom-cnt-horizontal > a:nth-child(3)"),
            (By.ID, "exportBtn"),
            (By.ID, "downloadCsv")
        ]
        
        for selector in buttons:
            button = wait.until(EC.element_to_be_clickable(selector))
            actions.move_to_element(button).click().perform()
        
        time.sleep(2)
        return get_latest_file(download_dir, before_download)
    
    finally:
        driver.quit()

def extract_transform_values(transform_str):
    """
    Extract translate values from SVG transform attribute.
    
    Args:
        transform_str (str): SVG transform attribute string
        
    Returns:
        tuple: (x, y) translation values
    """
    if not transform_str:
        return 0, 0
    
    match = re.search(r'translate\((\d+),(\d+)\)', transform_str)
    if match:
        try:
            return float(match.group(1)), float(match.group(2))
        except ValueError:
            pass
    return 0, 0

def basic_extract_svg_data(svg_path):
    """
    Extract coordinate data and labels from SVG chart.
    
    Args:
        svg_path (str): Path to SVG file
        
    Returns:
        tuple: (coordinates, x_labels, y_labels, transform_x, transform_y)
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()
    namespace = {'svg': 'http://www.w3.org/2000/svg'}
    
    path_group = root.find(".//svg:g[@class='highcharts-series highcharts-series-0 highcharts-line-series']", namespace)
    path = root.find(".//svg:path[@class='highcharts-graph']", namespace)
    
    transform_x, transform_y = extract_transform_values(path_group.get('transform', ''))
    coordinates = re.findall(r'[ML] ([\d.]+) ([\d.]+)', path.get('d', ''))
    
    # Extract y-axis labels
    y_labels = []
    used_positions = set()
    for elem in root.findall(".//svg:g[@class='highcharts-axis-labels highcharts-yaxis-labels']/svg:text", namespace):
        y_pos = float(elem.get('y', '0'))
        if y_pos in used_positions:
            continue
            
        tspan = elem.find('svg:tspan', namespace)
        value_text = tspan.text if tspan is not None else elem.text
        if value_text and value_text != '0':
            value = float(value_text.replace(',', ''))
            y_labels.append((y_pos, value))
            used_positions.add(y_pos)
    
    # Extract x-axis labels
    x_labels = []
    for elem in root.findall(".//svg:g[@class='highcharts-axis-labels highcharts-xaxis-labels']/svg:text", namespace):
        if elem.text:
            try:
                x_labels.append((float(elem.get('x', '0')), int(elem.text.strip())))
            except ValueError:
                continue
    
    return coordinates, sorted(x_labels), sorted(y_labels), transform_x, transform_y

def map_coordinate(pixel, labels, transform=0):
    """
    Map pixel coordinates to actual values using interpolation/extrapolation.
    
    Args:
        pixel (float): SVG coordinate to map
        labels (list): List of (position, value) tuples for mapping
        transform (float): SVG transform offset to apply
        
    Returns:
        float: Mapped value, or None if mapping fails
        
    Raises:
        ValueError: If insufficient labels for mapping
    """
    if not labels or len(labels) < 2:
        raise ValueError(f"Not enough labels for mapping (got {len(labels)})")
        
    positions = np.array([float(pos) for pos, _ in sorted(labels)])
    values = np.array([float(val) for _, val in sorted(labels)])
    
    # Adjust for transform
    adjusted = pixel + transform
    
    try:
        # Use scipy's interp1d for better interpolation/extrapolation
        interpolator = interp1d(positions, values, fill_value='extrapolate')
        return float(interpolator(adjusted))
    except Exception as e:
        print(f"Error in coordinate mapping: {e}")
        print(f"Positions: {positions}")
        print(f"Values: {values}")
        print(f"Adjusted pixel: {adjusted}")
        raise

def process_data_points(data_points, x_labels, y_labels, transform_x, transform_y):
    """
    Convert SVG coordinates to actual dates and prices.
    
    Args:
        data_points (list): List of (x, y) coordinate tuples from SVG
        x_labels (list): List of (position, year) tuples for x-axis
        y_labels (list): List of (position, price) tuples for y-axis
        transform_x (float): X-axis SVG transform offset
        transform_y (float): Y-axis SVG transform offset
        
    Returns:
        list: Processed points as [(datetime, price), ...]
    """
    processed_points = []
    
    for x, y in data_points:
        x, y = float(x), float(y)
        price = map_coordinate(y, y_labels, transform_y)
        date_val = map_coordinate(x, x_labels, transform_x)
        
        if price is not None and date_val is not None:
            date_obj = datetime(year=int(date_val), month=1, day=1) + \
                      timedelta(days=((date_val % 1) * 365.25))
            processed_points.append((date_obj, price))
    
    return processed_points

def cleanup_svg_files(filepath):
    """
    Delete downloaded SVG files after processing.
    
    Args:
        filepath (str): Path to the SVG file to delete
    """
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Warning: Failed to delete SVG file {filepath}: {e}")

def process_commodity(commodity):
    """
    Process a commodity by downloading its chart and extracting price data.
    
    Args:
        commodity (str): Name of commodity to process (e.g., "lithium", "lead", "cobalt")
        
    Returns:
        list: List of (datetime, price) tuples representing the price history,
             or None if processing fails
        
    Note:
        Downloads SVG chart from Trading Economics, extracts coordinate data,
        and converts SVG coordinates to actual dates and prices.
    """
    svg_file = download_chart(commodity)
    if not svg_file:
        return None
    
    try:
        data_points, x_labels, y_labels, transform_x, transform_y = basic_extract_svg_data(svg_file)
        return process_data_points(data_points, x_labels, y_labels, transform_x, transform_y)
    finally:
        cleanup_svg_files(svg_file)

def plot_df(df):
    """
    Create subplots for each commodity's price history.
    
    Args:
        df (DataFrame): Pandas DataFrame with columns [Date, Price, Commodity]
        
    Displays:
        Multiple line plots, one per commodity, sharing x-axis
    """
    commodities = df["Commodity"].unique()
    
    fig, axes = plt.subplots(1, len(commodities), figsize=(15, 5), sharex=True)
    
    for ax, commodity in zip(axes, commodities):
        sub_df = df[df["Commodity"] == commodity]
        sns.lineplot(data=sub_df, x="Date", y="Price", ax=ax)
        ax.set_title(commodity)
        ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig('10y_commodity_prices.png')
    plt.show()

if __name__ == "__main__":
    commodities = ["lithium", "lead", "cobalt"]
    
    # Process commodities
    results = {}
    for commodity in commodities:
        points = process_commodity(commodity)
        if points:
            results[commodity] = points
        else:
            print(f"Failed to process {commodity}")
    
    if results:
        # Create DataFrame
        dfs = []
        for commodity, points in results.items():
            df = pd.DataFrame(points, columns=['Date', 'Price'])
            df['Commodity'] = commodity
            dfs.append(df)
        
        df = pd.concat(dfs)
        df['Date'] = pd.to_datetime(df['Date'])
        df.to_csv('commodity_prices.csv', index=False)

        # show the plot
        plot_df(df)