import time
import requests
import json
import pandas as pd
import getopt
import re
import sys
import os
import urllib.parse
from dotenv import load_dotenv
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time

headless = ""
sleep_time_between_pages = 2
cards_header = ["Name", "Treatment", "Name Without Treatment", "Set", "Rarity", "Quantity", "Condition/Language", "Price", "Image URL", "Product URL"]
wanted_cards_header = ["Quantity", "Name"]
found_cards_header = ["Name"]

def is_json(myjson):
  """Checks to see if the given string is valid JSON

    Args:
        myjson (string): string representing the JSON

    Returns:
        bool: True if valid JSON, False if not
    """
  try:
    json.loads(myjson)
  except ValueError as e:
    return False
  return True

def get_my_store_id():
    """Returns store id from your store. This is no longer used by the script, but is here if for some reason you want to use it. You'll need an API key defined in a constants.py file. 

    Returns:
        JSON: store id
    """

    url = os.getenv("TCG_PLAYER_API_BASE_URL") + "/stores/self"
    
    headers = {"accept": "application/json", "Authorization": "bearer " + os.getenv("TCG_PLAYER_API_KEY")}
    
    response = requests.get(url, headers=headers)

    if (is_json(response.text)):
        resp_json = json.loads(response.text)     

        if "results" in resp_json and len(resp_json["results"]) > 0:  
            return resp_json["results"][0]
    
    return ""

def get_store_id(store_name):
    """Returns store id from the TCGPlayer API. This is no longer used by the script, but is here if for some reason you want to use it. You'll need an API key defined in a constants.py file. 

    Args:
        store_name (string): store_name

    Returns:
        JSON: store id
    """

    url = os.getenv("TCG_PLAYER_API_BASE_URL") + "/stores?name=" + store_name
    
    headers = {"accept": "application/json", "Authorization": "bearer " + os.getenv("TCG_PLAYER_API_KEY")}
    
    response = requests.get(url, headers=headers)

    if (is_json(response.text)):
        resp_json = json.loads(response.text)        

        if "results" in resp_json and len(resp_json["results"]) > 0:  
            return resp_json["results"][0]
    
    return ""

def get_store_info(store_key):
    """Returns store info from the TCGPlayer API. This is no longer used by the script, but is here if for some reason you want to use it. You'll need an API key defined in a constants.py file. 

    Args:
        store_key (string): store_key (from TCGPlayer) representing the store.

    Returns:
        JSON: store info from the /stores/ endpoint.
    """

    url = os.getenv("TCG_PLAYER_API_BASE_URL") + "/stores/" + store_key
    
    headers = {"accept": "application/json", "Authorization": "bearer " + os.getenv("TCG_PLAYER_API_KEY")}
    
    response = requests.get(url, headers=headers)

    if (is_json(response.text)):
        resp_json = json.loads(response.text)    

        if "results" in resp_json and len(resp_json["results"]) > 0:  
            return resp_json["results"][0]
    
    return ""

def scrape_store_inventory(driver, store_front_url, set_name):
    """Goes through the store and scrapes all of the MTG inventory via the list page since it gives us more data than the grid view. Returns a list of cards.

    Args:
        driver (selenium driver): active selenium driver
        store_front_url (string): base URL for the store via TCGPlayer Pro, example: https://nolandbeyond.tcgplayerpro.com/
        set_name (string): name of the set from the Set Name filter. Needed as TCGPlayer limits us to around 10k cards when going through pagination, so sets allow us to get under that.

    Returns:
        list: list of cards with the following fields: "Name", "Treatment", "Name Without Treatment", "Set", "Rarity", "Quantity", "Condition/Language", "Price", "Image URL", "Product URL"
    """

    # We'll want to restrict to the product search, particularly only for MTG cards
    # /search/products?q=&productLineName=Magic:+The+Gathering&pageSize=48
    # Do an initial page load to get page count
    url = store_front_url + "search/products?q=&productLineName=Magic:+The+Gathering&pageSize=48&view=list&page=1"

    if set_name:
        set_qs = { "setName": set_name }
        url = url + "&" + urllib.parse.urlencode(set_qs)

    # Get number of pages available, first
    driver.get(url)

    # Waiting for web requests to finish. Yeah, better ways to do this. Sue me.
    driver.implicitly_wait(sleep_time_between_pages)

    try:
        last_page = driver.find_element(By.CSS_SELECTOR, ".tcg-pagination .tcg-pagination__pages .tcg-standard-button--flat:nth-last-child(1)")
        total_pages = 1
        if last_page:
            total_pages = int(last_page.text)
    except Exception as e:
        total_pages = 1

    # Looks like TCGPlayer may limit how many pages with pageSize=48 somebody can go. Looks like the stopper is something like 208. Which is nearly 10k cards.
    # Tried 36 as the number per page, and the top limit is around 277 pages which is also right near 10k cards. 
    # Tried 24 as the number per page, and my hunch was it'd stop at double the 48 pageSize (416). And this was true, too. So, looks like TCGPlayer doesn't want you to go more
    # than 10k products deep.
    # So, that's why we're scraping by set

    all_cards = []
    for page_number in range(total_pages):
        if page_number == 0:
            # Setting URL empty for page 1, since we're already on it. Save an unnecessary call.
            cards = scrape_store_page_contents_list_view(driver, "")
        else:
            paginated_url = store_front_url + "search/products?q=&productLineName=Magic:+The+Gathering&pageSize=48&view=list&page=" + str(page_number+1)

            if set_name:
                set_qs = { "setName": set_name }
                paginated_url = paginated_url + "&" + urllib.parse.urlencode(set_qs)

            cards = scrape_store_page_contents_list_view(driver, paginated_url)

        # Might hit the end of the line of cards
        if len(cards) == 0:
            break

        for card in cards:
            all_cards.append(card)

    return all_cards

def scroll_to_bottom(driver, height_increment):
    """Scrolls to the bottom of the page in increments. This is typically done in the case of lazy loading images so that the image URL can be retrieved or if a page is dynamically loading other content.

    Args:
        driver (selenium driver): active selenium driver
        height_increment (int): height increment to scroll
    """

    scroll_height = driver.execute_script("return document.body.scrollHeight;")
    increment = height_increment

    for i in range(0, scroll_height, increment):
        driver.execute_script(f"window.scrollTo(0, {i});")
        time.sleep(0.10)

def get_card_treatment(name):
    """Returns the treatment with parenthesis removed. If more than one treatment, it'll be return comma delimited.

    Args:
        name (string): full name of the card including treatment. Example: Barrowgoyf (Extended Art) (Ripple Foil)

    Returns:
        string: treatment, comma delimited if more than one. If no treatment, returns empty string.
    """

    if name:
        matches = re.findall(r'\((.*?)\)', name)

        if matches:
            return ",".join(matches)

    return ""

def remove_card_treatment_info(name):
    """Removes the treatment from the card name.

    Args:
        name (string): full name of the card including treatment. Example: Barrowgoyf (Extended Art) (Ripple Foil)

    Returns:
        string: name of the card with the treatment removed.
    """

    if name:
        return re.sub("[\(\[].*?[\)\]]", "", name)
    
    return name

def scrape_store_page_contents_list_view(driver, url):
    """Hits the URL (if supplied). If URL not supplied, will scrape current page. Returns a list of cards.

    Args:
        driver (selenium driver): active selenium driver
        url (string): list page URL to scrape for, typically with the page number applied: https://nolandbeyond.tcgplayerpro.com/search/products?q=&productLineName=Magic:+The+Gathering&pageSize=48&view=list&page=1. If empty, will scrape current page in driver.

    Returns:
        list: list of cards with the following fields: "Name", "Treatment", "Name Without Treatment", "Set", "Rarity", "Quantity", "Condition/Language", "Price", "Image URL", "Product URL"
    """

    # div.search-results-list__info
    #   image:              div.search-results-list__image-container img
    #   card info:          div.search-results-list__card-info
    #       name:           .search-results-list__name
    #       rarity:         .search-results-list__rarity (Strip out "Rarity: ")
    #       set:            .search-results-list__set (Strip out "Set: )
    #       URL:            a.search-results-list__details
    #   SKUs:               div.search-results-list__skus
    #       list item:      .sku-list__list-item
    #           price:      .sku-list__price
    #           condition:  .sku-list__condition (might also have language, i.e. Heavily Played Foil - English)
    #           quantity:   .tcg-quantity-selector__max-available  (Strip "of ")
    #       
    if url:
        driver.get(url)

    # this is only here so we don't go crazy with the web requests
    time.sleep(sleep_time_between_pages)

    scroll_to_bottom(driver, 800)

    cards = []
    found_cards = driver.find_elements(By.CSS_SELECTOR, 'div.search-results-list__info')

    for card in found_cards:
        name = card.find_element(By.CSS_SELECTOR, ".search-results-list__name").text
        name_without_treatment = remove_card_treatment_info(name)
        treatment = get_card_treatment(name)

        # TODO: Make a basic name that doesn't have alternate print names so we can try and do a catchall. Need to find the right way to pattern match this.
        set = ""

        try:   
            set_holder = card.find_element(By.CSS_SELECTOR, ".search-results-list__set")
            if (set_holder):
                set = set_holder.text.replace("Set: ", "")
        except Exception as e:
            set = ""
         
        rarity = ""

        # sometimes, no rarity (i.e. Secret Lair packs)
        try:
            rarity_holder = card.find_element(By.CSS_SELECTOR, ".search-results-list__rarity")
            if (rarity_holder):
                rarity = rarity_holder.text.replace("Rarity: ", "")
        except Exception as e:
            rarity = ""
        
        product_url = card.find_element(By.CSS_SELECTOR, "a.search-results-list__details").get_attribute("href")

        image_url = ""

        # for some reason, grabbing the SRC of the image on the list page is absurdly slow, so we are going to construct the URL based on card id found in product detail page
        # format follows: https://tcgplayer-cdn.tcgplayer.com/product/{id}_200w.jpg
        # example: https://tcgplayer-cdn.tcgplayer.com/product/282745_200w.jpg
        if product_url:
            parts = product_url.split("/")
            card_id = parts[-1]
            image_url = "https://tcgplayer-cdn.tcgplayer.com/product/" + card_id + "_200w.jpg"

        # This has SKUs, so we'll go through each (i.e. multiple conditions) and add them as individual list items
        card_skus = card.find_elements(By.CSS_SELECTOR, ".sku-list__list-item")
        for sku in card_skus:
            price = sku.find_element(By.CSS_SELECTOR, ".sku-list__price").text
            condition_language = sku.find_element(By.CSS_SELECTOR, ".sku-list__condition").text
            quantity = sku.find_element(By.CSS_SELECTOR, ".tcg-quantity-selector__max-available").text.replace("of ", "")

            card = [name, treatment, name_without_treatment, set, rarity, quantity, condition_language, price, image_url, product_url]
            cards.append(card)

    return cards

def load_desired_cards_from_file(file_location):
    """Attempts to load the desired cards to search against store inventory from a txt file hat is space delimited. Format is: {qty} {name}. Reference example in desired_cards_example.txt.

    Args:
        file_location (string): file_location for wanted cards text file. 

    Returns:
        list: list of desired cards with quantity and name as fields.
    """

    desired_cards = []

    if not file_location:
        return desired_cards

    try:
        with open(file_location, "r") as f:
            file_content = f.read()

        if not file_content:
            print("no data found in file " + file_location)
            return desired_cards
        
        # format in file is {qty} {card name}
        cards = file_content.splitlines()
        for card in cards:
            card_parts = card.split(None, 1)

            desired_card = [card_parts[0], card_parts[1]]
            desired_cards.append(desired_card)

        return desired_cards

    except Exception as e:
        print(e)
        return desired_cards

def column(matrix, column_index):
    """Returns the column from the matrix based on the supplied column_index

    Args:
        column_index (int): index (zero based) of the column to retrieve.

    Returns:
        list: rows for the given column index.
    """

    return [row[column_index] for row in matrix]

def find_wanted_cards_dataframe(store_card_inventory, wanted_cards):
    """Returns a dataframe represented a filtered list of the supplied store_card_inventory list based on the wanted_cards name.

    Args:
        store_card_inventory (list): list of store card inventory to search wanted_cards against
        wanted_cards (list): list of card names to search store_card_inventory against

    Returns:
        dataframe: dataframe based on matched wanted_cards
    """

    # let's use pandas to grab rows from scraped site so that all of the columns are visible so users can quickly see things like price, condition, etc. instead of just card name
    wanted_card_names = column(wanted_cards, 1)

    # Get dataframe to query against
    cards_df = pd.DataFrame(data = store_card_inventory, columns = cards_header)
    found_cards_df = cards_df[cards_df["Name"].isin(wanted_card_names)] 

    return found_cards_df

def write_to_excel(store_card_inventory, wanted_cards, found_cards_df):
    """Writes the store_card_inventory list, wanted_cards list, and found_cards_df dataframe to an Excel file called tcg_player_inventory_for_Store.xlsx

    Args:
        store_card_inventory (list): scraped store_card_inventory list
        wanted_cards (list): list of wanted cards
        found_cards_df (dataframe): data frame of found cards, most likely from find_wanted_cards_dataframe
    """

    cards_df = pd.DataFrame(data = store_card_inventory, columns = cards_header)
    wanted_cards_df = pd.DataFrame(data = wanted_cards, columns = wanted_cards_header)
 
    writer = pd.ExcelWriter("tcg_player_inventory_for_store.xlsx", engine = "xlsxwriter", engine_kwargs={"options": {"strings_to_urls": False}})

    cards_df.to_excel(writer, index=False, sheet_name = "Store Inventory")
    wanted_cards_df.to_excel(writer, index=False, sheet_name = "Wanted Cards")
    found_cards_df.to_excel(writer, index=False, sheet_name = "Found Cards")
    
    writer.close()

def get_sets(driver, store_front_url):
    """Retrieves a list of M:TG sets available from the given store_front_url.

    Args:
        driver (selenium driver): active selenium driver
        store_front_url (string): base URL for the store via TCGPlayer Pro, example: https://nolandbeyond.tcgplayerpro.com/

    Returns:
        list: list of set names
    """

    url = store_front_url + "search/products?q=&productLineName=Magic:+The+Gathering&pageSize=48&view=list"
    sets = []

    driver.get(url)

    time.sleep(sleep_time_between_pages)

    try:
        found_panels = driver.find_elements(By.CSS_SELECTOR, 'div.tcg-accordion-panel')

        for found_panel in found_panels:
            header = found_panel.find_element(By.CSS_SELECTOR, "div.tcg-accordion-panel-header")
            header_content = found_panel.find_element(By.CSS_SELECTOR, "span.tcg-accordion-panel-header__content")

            if header_content and (header_content.text.lower() == "set name"):
                # Check if already expanded
                if "is-open" not in header.get_attribute("class"):
                    # Expand to get sets
                    action_chains = ActionChains(driver)
                    action_chains.move_to_element(header_content).click().perform()

                set_names = found_panel.find_elements(By.CSS_SELECTOR, ".tcg-input-checkbox__label-text div > div:first-child")
                if set_names:
                    for set_name in set_names:
                        sets.append(set_name.text)

    except Exception as e:
        print(e)
    
    return sets

def setup_selenium_driver():
    """Sets up the Selenium driver based on a variety of settings.
    """

    options = ChromeOptions()

    # Does not like headless due to out of bounds, will need to look into this. Trying the headless=new flag for full featured Chrome, but new headless implementation
    # Headless=new requires Chrome 109. Need to add the Chrome installation dependency.
    if headless:
        options.add_argument(headless)

    options.add_argument('--start-maximized')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    driver = Chrome(options=options)

    return driver

def scrape_store_by_sets(store_front_url):
    """Scrapes the entire store for M:TG cards on a per set basis to avoid 10k card limit via pagination.

    Args:
        store_front_url (string): base URL for the store via TCGPlayer Pro, example: https://nolandbeyond.tcgplayerpro.com/

    Returns:
        list: list of cards
    """

    driver = setup_selenium_driver()

    sets = get_sets(driver, store_front_url)
    store_card_inventory = []

    if sets:
        for set in sets:
            store_card_set_inventory = []
            print("Scraping by set name: " + set)
            store_card_set_inventory += scrape_store_inventory(driver, store_front_url, set)
            print("Cards found in set: " + str(len(store_card_set_inventory)))

            store_card_inventory += store_card_set_inventory

    return store_card_inventory

def main(argv):
    # defaults
    store_name = ""
    store_url = ""
    want_file_location = ""

    try:
        opts, args = getopt.getopt(argv,"s:u:w:h",["store-name=","store-url=","want-file-location=","headless-flag="])
    except getopt.GetoptError:
        print('tcg_player_searcher.py -s <store-name> -u <store-url> -w <want-file-location> -h <headless-flag>')
        print("store-url is the TCGPlayer Pro store URL. If provided, store-name will be bypassed and the store URL will be directly used and no API calls will be made to find store information.")
        print("store-name is the official TCG Player store name to look for")
        print("want-file-location is the file location for a list of card names (in a text file) that you're looking to find for the store")
        print("headless-flag is the Selenium/Chrome flag to run headless. Values can be: empty (won't run headless), --headless (old headless for Chrome < v109), and --headless=new for full Chrome but headless (Chrome >= v109)")
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-s", "--store-name"):
            store_name = arg      
        if opt in ("-u", "--store-url"):
            store_url = arg      
        if opt in ("-w", "--want-file-location"):
            want_file_location = arg
        if opt in ("-h", "--headless-flag"):
            headless = arg   

    # Store name is mandatory
    if not store_name and not store_url:
        print("Please provide store name or a store URL. Exiting.")
        sys.exit(2)

    load_dotenv()

    desired_cards = []
    if want_file_location:
        desired_cards = load_desired_cards_from_file(want_file_location)

    start = time.time()

    if store_name:
        store_id = get_store_id(store_name)

        if not store_id:
            print("No store found. Exiting.")
            sys.exit(2)

        store_front_url = get_store_info(store_id)["storefrontUrl"]
        if not store_front_url:
            print("No corresponding store url found. Exiting.")
            sys.exit(2)

        print("Store: " + store_name)
        print("Store id: " + store_id)
    else:
        store_front_url = store_url

    print("Store URL: " + store_front_url)
    print("Total desired cards to search for: " + str(len(desired_cards)))

    store_card_inventory = scrape_store_by_sets(store_front_url)
    found_cards_in_inventory_df = find_wanted_cards_dataframe(store_card_inventory, desired_cards)

    write_to_excel(store_card_inventory, desired_cards, found_cards_in_inventory_df)

    end = time.time()
    elapsed_time = end - start
    total_cards_scraped = len(store_card_inventory)
    cards_scraped_per_second = total_cards_scraped / elapsed_time

    print("Script run time: " + str(elapsed_time))
    print("Cards scraped: " + str(total_cards_scraped))
    print("Cards scraped per second: " + str(cards_scraped_per_second))

if __name__ == "__main__":
    main(sys.argv[1:])