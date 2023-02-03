import requests

cookies = {
    "PHPSESSID": "k1ukjiselkhb5puck5d0jokv27",
    "ure-cookie-policy-agree": "1",
    "_yoid": "884763f7-bef5-40a6-83df-1545334da11e",
    "_yosid": "cefd11b3-7e7e-4430-86cf-b8bc00e0e656",
    "Vendor": "pco90umcsi8hqdg4p4iora571m",
    "ure-ds-cookie-policy-agree": "1",
    "_gid": "GA1.2.55996015.1649815514",
    "ureBrowserSession": "1649815513746661517500",
    "ureServerSession": "1649815513746661517500",
    "_ga_PSJFQK2M2M": "GS1.1.1649815513.5.1.1649817015.0",
    "_ga": "GA1.2.818611543.1645503200",
    "_gat_gtag_UA_3153503_1": "1",
}

headers = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    # Requests sorts cookies= alphabetically
    # 'Cookie': 'PHPSESSID=k1ukjiselkhb5puck5d0jokv27; ure-cookie-policy-agree=1; _yoid=884763f7-bef5-40a6-83df-1545334da11e; _yosid=cefd11b3-7e7e-4430-86cf-b8bc00e0e656; Vendor=pco90umcsi8hqdg4p4iora571m; ure-ds-cookie-policy-agree=1; _gid=GA1.2.55996015.1649815514; ureBrowserSession=1649815513746661517500; ureServerSession=1649815513746661517500; _ga_PSJFQK2M2M=GS1.1.1649815513.5.1.1649817015.0; _ga=GA1.2.818611543.1645503200; _gat_gtag_UA_3153503_1=1',
    "Origin": "https://www.utahrealestate.com",
    "Pragma": "no-cache",
    "Referer": "https://www.utahrealestate.com/search/map.search/type/7",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

data = "param=geometry&value=POLYGON%28%28-112.05912787389674%2040.635592922233%2C-112.05912787389674%2040.88718086340279%2C-111.73538485714992%2040.88718086340279%2C-111.73538485714992%2040.635592922233%2C-112.05912787389674%2040.635592922233%29%29&chain=saveLocation,criteriaAndCountAction,mapInlineResultsAction&all=1&accuracy=&geocoded=&state=&box=&htype=&lat=&lng=&selected_listno=&type=7&geolocation=&listprice1=&listprice2=&tot_bed1=&tot_bath1=&o_env_certification=32&status=1&leaseduration=255&tot_sqf1=&o_seniorcommunity=1&o_has_hoa=1&status=1&loc=&accr=&op=16777216&advanced_search=0&param_reset=housenum,dir_pre,street,streettype,dir_post,city,county_code,zip,area,subdivision,quadrant,unitnbr1,unitnbr2,geometry,coord_ns1,coord_ns2,coord_ew1,coord_ew2,housenum,o_dir_pre,o_street,o_streettype,o_dir_post,o_city,o_county_code,o_zip,o_area,o_subdivision,o_quadrant,o_unitnbr1,o_unitnbr2,o_geometry,o_coord_ns1,o_coord_ns2,o_coord_ew1,o_coord_ew2"

response = requests.post(
    "https://www.utahrealestate.com/search/chained.update/param_reset/county_code,o_county_code,city,o_city,zip,o_zip,geometry,o_geometry/count/false/criteria/false/pg/1/limit/50/dh/671/using_map_viewport/true",
    headers=headers,
    cookies=cookies,
    data=data,
)

response.raise_for_status()
d = response.json()
print(d["listing_data"])
