"""
State and local sales tax rate database.

Covers all 50 US states plus DC, with base state rates and common local
jurisdiction surcharges. Rates current as of 2024 legislative sessions.

Sources: State revenue department publications, Tax Foundation compilations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ExemptionCategory(Enum):
    """Standard sales tax exemption categories recognized across states."""

    GROCERY = "grocery"
    CLOTHING = "clothing"
    PRESCRIPTION_DRUG = "prescription_drug"
    MEDICAL_DEVICE = "medical_device"
    MANUFACTURING_EQUIPMENT = "manufacturing_equipment"
    AGRICULTURAL = "agricultural"
    RESALE = "resale"
    NONPROFIT = "nonprofit"
    GOVERNMENT = "government"
    DIGITAL_GOODS = "digital_goods"
    SOFTWARE_SAAS = "software_saas"


@dataclass(frozen=True)
class LocalRate:
    """A local jurisdiction tax rate overlay."""

    jurisdiction: str
    county: str
    rate: float  # decimal, e.g. 0.02 = 2%
    jurisdiction_type: str = "city"  # city, county, district


@dataclass
class StateRate:
    """Complete tax rate profile for a single state."""

    state_code: str
    state_name: str
    base_rate: float  # decimal
    has_local_taxes: bool = True
    max_local_rate: float = 0.0
    avg_combined_rate: float = 0.0
    exemptions: list[ExemptionCategory] = field(default_factory=list)
    local_rates: list[LocalRate] = field(default_factory=list)
    filing_frequency_threshold: dict[str, float] = field(default_factory=dict)
    notes: str = ""


# ---------------------------------------------------------------------------
# Full 50-state + DC rate database
# ---------------------------------------------------------------------------

_STATE_DATA: dict[str, dict] = {
    "AL": {
        "name": "Alabama",
        "base_rate": 0.04,
        "has_local": True,
        "max_local": 0.075,
        "avg_combined": 0.0924,
        "exemptions": [ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Birmingham", "Jefferson", 0.04),
            LocalRate("Montgomery", "Montgomery", 0.035),
            LocalRate("Mobile", "Mobile", 0.04),
            LocalRate("Huntsville", "Madison", 0.03),
        ],
        "notes": "Origin-based sourcing. Self-administered local taxes.",
    },
    "AK": {
        "name": "Alaska",
        "base_rate": 0.0,
        "has_local": True,
        "max_local": 0.075,
        "avg_combined": 0.0182,
        "exemptions": [],
        "locals": [
            LocalRate("Juneau", "Juneau", 0.05),
            LocalRate("Kodiak", "Kodiak Island", 0.07),
        ],
        "notes": "No state sales tax. Localities may impose their own.",
    },
    "AZ": {
        "name": "Arizona",
        "base_rate": 0.056,
        "has_local": True,
        "max_local": 0.058,
        "avg_combined": 0.0840,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Phoenix", "Maricopa", 0.023),
            LocalRate("Tucson", "Pima", 0.026),
            LocalRate("Scottsdale", "Maricopa", 0.0175),
            LocalRate("Mesa", "Maricopa", 0.0175),
        ],
        "notes": "TPT (Transaction Privilege Tax), origin-based.",
    },
    "AR": {
        "name": "Arkansas",
        "base_rate": 0.065,
        "has_local": True,
        "max_local": 0.0625,
        "avg_combined": 0.0951,
        "exemptions": [ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Little Rock", "Pulaski", 0.03),
            LocalRate("Fort Smith", "Sebastian", 0.0275),
        ],
        "notes": "Grocery taxed at reduced 0.125% state rate.",
    },
    "CA": {
        "name": "California",
        "base_rate": 0.0725,
        "has_local": True,
        "max_local": 0.0375,
        "avg_combined": 0.0882,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [
            LocalRate("Los Angeles", "Los Angeles", 0.025),
            LocalRate("San Francisco", "San Francisco", 0.0125),
            LocalRate("San Diego", "San Diego", 0.0075),
            LocalRate("San Jose", "Santa Clara", 0.0125),
            LocalRate("Sacramento", "Sacramento", 0.0075),
        ],
        "notes": "Destination-based sourcing. CDTFA administers.",
    },
    "CO": {
        "name": "Colorado",
        "base_rate": 0.029,
        "has_local": True,
        "max_local": 0.083,
        "avg_combined": 0.0777,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Denver", "Denver", 0.0481),
            LocalRate("Colorado Springs", "El Paso", 0.031),
            LocalRate("Aurora", "Arapahoe", 0.0375),
        ],
        "notes": "Home-rule cities self-administer. Complex local landscape.",
    },
    "CT": {
        "name": "Connecticut",
        "base_rate": 0.0635,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.0635,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.CLOTHING,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [],
        "notes": "Clothing under $50 exempt. Luxury tax 7.75% on vehicles > $50k.",
    },
    "DE": {
        "name": "Delaware",
        "base_rate": 0.0,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.0,
        "exemptions": [],
        "locals": [],
        "notes": "No sales tax. Gross receipts tax applies to sellers instead.",
    },
    "FL": {
        "name": "Florida",
        "base_rate": 0.06,
        "has_local": True,
        "max_local": 0.025,
        "avg_combined": 0.0702,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.PRESCRIPTION_DRUG,
            ExemptionCategory.MEDICAL_DEVICE,
        ],
        "locals": [
            LocalRate("Miami", "Miami-Dade", 0.01),
            LocalRate("Orlando", "Orange", 0.005),
            LocalRate("Tampa", "Hillsborough", 0.015),
            LocalRate("Jacksonville", "Duval", 0.005),
        ],
        "notes": "Destination-based. DR-15 monthly/quarterly return.",
    },
    "GA": {
        "name": "Georgia",
        "base_rate": 0.04,
        "has_local": True,
        "max_local": 0.05,
        "avg_combined": 0.0735,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Atlanta", "Fulton", 0.0389),
            LocalRate("Savannah", "Chatham", 0.04),
        ],
        "notes": "Destination-based. LOST/SPLOST local option taxes.",
    },
    "HI": {
        "name": "Hawaii",
        "base_rate": 0.04,
        "has_local": True,
        "max_local": 0.005,
        "avg_combined": 0.0444,
        "exemptions": [ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Honolulu", "Honolulu", 0.005),
        ],
        "notes": "GET (General Excise Tax) on gross receipts, not a true sales tax.",
    },
    "ID": {
        "name": "Idaho",
        "base_rate": 0.06,
        "has_local": True,
        "max_local": 0.03,
        "avg_combined": 0.0602,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Sun Valley", "Blaine", 0.03, "district"),
        ],
        "notes": "Destination-based. Resort city local option.",
    },
    "IL": {
        "name": "Illinois",
        "base_rate": 0.0625,
        "has_local": True,
        "max_local": 0.0525,
        "avg_combined": 0.0882,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.PRESCRIPTION_DRUG,
            ExemptionCategory.MEDICAL_DEVICE,
        ],
        "locals": [
            LocalRate("Chicago", "Cook", 0.0475),
            LocalRate("Springfield", "Sangamon", 0.0225),
            LocalRate("Naperville", "DuPage", 0.0175),
        ],
        "notes": "Origin-based. Grocery taxed at reduced 1% state rate.",
    },
    "IN": {
        "name": "Indiana",
        "base_rate": 0.07,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.07,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [],
        "notes": "Destination-based. Uniform state rate, no local sales taxes.",
    },
    "IA": {
        "name": "Iowa",
        "base_rate": 0.06,
        "has_local": True,
        "max_local": 0.01,
        "avg_combined": 0.0694,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Des Moines", "Polk", 0.01),
            LocalRate("Cedar Rapids", "Linn", 0.01),
        ],
        "notes": "Destination-based.",
    },
    "KS": {
        "name": "Kansas",
        "base_rate": 0.065,
        "has_local": True,
        "max_local": 0.05,
        "avg_combined": 0.0872,
        "exemptions": [ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Wichita", "Sedgwick", 0.0225),
            LocalRate("Topeka", "Shawnee", 0.0215),
        ],
        "notes": "Grocery taxed at full rate (phase-down in progress).",
    },
    "KY": {
        "name": "Kentucky",
        "base_rate": 0.06,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.06,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [],
        "notes": "Destination-based. Uniform state rate.",
    },
    "LA": {
        "name": "Louisiana",
        "base_rate": 0.0445,
        "has_local": True,
        "max_local": 0.07,
        "avg_combined": 0.0955,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("New Orleans", "Orleans", 0.05),
            LocalRate("Baton Rouge", "East Baton Rouge", 0.05),
        ],
        "notes": "Destination-based. Separate state and local returns.",
    },
    "ME": {
        "name": "Maine",
        "base_rate": 0.055,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.055,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [],
        "notes": "Destination-based.",
    },
    "MD": {
        "name": "Maryland",
        "base_rate": 0.06,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.06,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.CLOTHING,
            ExemptionCategory.PRESCRIPTION_DRUG,
            ExemptionCategory.MEDICAL_DEVICE,
        ],
        "locals": [],
        "notes": "Destination-based. Digital goods taxable.",
    },
    "MA": {
        "name": "Massachusetts",
        "base_rate": 0.0625,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.0625,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.CLOTHING,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [],
        "notes": "Clothing under $175 exempt. Destination-based.",
    },
    "MI": {
        "name": "Michigan",
        "base_rate": 0.06,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.06,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [],
        "notes": "Destination-based. Uniform state rate.",
    },
    "MN": {
        "name": "Minnesota",
        "base_rate": 0.06875,
        "has_local": True,
        "max_local": 0.02,
        "avg_combined": 0.0783,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.CLOTHING,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [
            LocalRate("Minneapolis", "Hennepin", 0.02),
            LocalRate("St. Paul", "Ramsey", 0.0175),
        ],
        "notes": "Destination-based.",
    },
    "MS": {
        "name": "Mississippi",
        "base_rate": 0.07,
        "has_local": True,
        "max_local": 0.01,
        "avg_combined": 0.0707,
        "exemptions": [ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Jackson", "Hinds", 0.01),
        ],
        "notes": "Origin-based. Grocery taxed at full rate.",
    },
    "MO": {
        "name": "Missouri",
        "base_rate": 0.04225,
        "has_local": True,
        "max_local": 0.0588,
        "avg_combined": 0.0825,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("St. Louis City", "St. Louis City", 0.049),
            LocalRate("Kansas City", "Jackson", 0.04),
            LocalRate("Springfield", "Greene", 0.0335),
        ],
        "notes": "Origin-based. Grocery taxed at reduced 1.225% state rate.",
    },
    "MT": {
        "name": "Montana",
        "base_rate": 0.0,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.0,
        "exemptions": [],
        "locals": [],
        "notes": "No sales tax. Resort tax in select areas.",
    },
    "NE": {
        "name": "Nebraska",
        "base_rate": 0.055,
        "has_local": True,
        "max_local": 0.02,
        "avg_combined": 0.0694,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Omaha", "Douglas", 0.02),
            LocalRate("Lincoln", "Lancaster", 0.0175),
        ],
        "notes": "Destination-based.",
    },
    "NV": {
        "name": "Nevada",
        "base_rate": 0.0685,
        "has_local": True,
        "max_local": 0.0153,
        "avg_combined": 0.0823,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Las Vegas", "Clark", 0.0138),
            LocalRate("Reno", "Washoe", 0.0098),
        ],
        "notes": "Destination-based.",
    },
    "NH": {
        "name": "New Hampshire",
        "base_rate": 0.0,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.0,
        "exemptions": [],
        "locals": [],
        "notes": "No sales tax. Meals and rooms tax (8.5%) applies separately.",
    },
    "NJ": {
        "name": "New Jersey",
        "base_rate": 0.06625,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.06625,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.CLOTHING,
            ExemptionCategory.PRESCRIPTION_DRUG,
            ExemptionCategory.MEDICAL_DEVICE,
        ],
        "locals": [],
        "notes": "Destination-based. UEZ zones have reduced 3.3125% rate.",
    },
    "NM": {
        "name": "New Mexico",
        "base_rate": 0.04875,
        "has_local": True,
        "max_local": 0.0481,
        "avg_combined": 0.0729,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Albuquerque", "Bernalillo", 0.0281),
            LocalRate("Santa Fe", "Santa Fe", 0.0344),
        ],
        "notes": "GRT (Gross Receipts Tax). Origin-based.",
    },
    "NY": {
        "name": "New York",
        "base_rate": 0.04,
        "has_local": True,
        "max_local": 0.0875,
        "avg_combined": 0.0852,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.CLOTHING,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [
            LocalRate("New York City", "New York", 0.045),
            LocalRate("Buffalo", "Erie", 0.04),
            LocalRate("Albany", "Albany", 0.04),
            LocalRate("Syracuse", "Onondaga", 0.04),
        ],
        "notes": "Destination-based. Clothing/footwear under $110 exempt in NYC.",
    },
    "NC": {
        "name": "North Carolina",
        "base_rate": 0.0475,
        "has_local": True,
        "max_local": 0.0275,
        "avg_combined": 0.0698,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Charlotte", "Mecklenburg", 0.025),
            LocalRate("Raleigh", "Wake", 0.0225),
            LocalRate("Durham", "Durham", 0.025),
        ],
        "notes": "Destination-based.",
    },
    "ND": {
        "name": "North Dakota",
        "base_rate": 0.05,
        "has_local": True,
        "max_local": 0.035,
        "avg_combined": 0.0696,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Fargo", "Cass", 0.025),
            LocalRate("Bismarck", "Burleigh", 0.02),
        ],
        "notes": "Destination-based.",
    },
    "OH": {
        "name": "Ohio",
        "base_rate": 0.0575,
        "has_local": True,
        "max_local": 0.0225,
        "avg_combined": 0.0724,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Columbus", "Franklin", 0.0175),
            LocalRate("Cleveland", "Cuyahoga", 0.0225),
            LocalRate("Cincinnati", "Hamilton", 0.02),
        ],
        "notes": "Origin-based. County permissive taxes.",
    },
    "OK": {
        "name": "Oklahoma",
        "base_rate": 0.045,
        "has_local": True,
        "max_local": 0.07,
        "avg_combined": 0.0895,
        "exemptions": [ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Oklahoma City", "Oklahoma", 0.0413),
            LocalRate("Tulsa", "Tulsa", 0.0467),
        ],
        "notes": "Origin-based. Grocery taxed at full rate.",
    },
    "OR": {
        "name": "Oregon",
        "base_rate": 0.0,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.0,
        "exemptions": [],
        "locals": [],
        "notes": "No sales tax.",
    },
    "PA": {
        "name": "Pennsylvania",
        "base_rate": 0.06,
        "has_local": True,
        "max_local": 0.02,
        "avg_combined": 0.0634,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.CLOTHING,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [
            LocalRate("Philadelphia", "Philadelphia", 0.02),
            LocalRate("Pittsburgh", "Allegheny", 0.01),
        ],
        "notes": "Origin-based. Most clothing exempt.",
    },
    "RI": {
        "name": "Rhode Island",
        "base_rate": 0.07,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.07,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.CLOTHING,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [],
        "notes": "Clothing under $250 exempt. Destination-based.",
    },
    "SC": {
        "name": "South Carolina",
        "base_rate": 0.06,
        "has_local": True,
        "max_local": 0.03,
        "avg_combined": 0.0746,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Charleston", "Charleston", 0.025),
            LocalRate("Columbia", "Richland", 0.02),
        ],
        "notes": "Destination-based. $300 tax cap on certain items.",
    },
    "SD": {
        "name": "South Dakota",
        "base_rate": 0.042,
        "has_local": True,
        "max_local": 0.045,
        "avg_combined": 0.064,
        "exemptions": [ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Sioux Falls", "Minnehaha", 0.02),
            LocalRate("Rapid City", "Pennington", 0.02),
        ],
        "notes": "Grocery taxed. Wayfair v. South Dakota (2018) originated here.",
    },
    "TN": {
        "name": "Tennessee",
        "base_rate": 0.07,
        "has_local": True,
        "max_local": 0.0275,
        "avg_combined": 0.0955,
        "exemptions": [ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Nashville", "Davidson", 0.0225),
            LocalRate("Memphis", "Shelby", 0.0225),
            LocalRate("Knoxville", "Knox", 0.0225),
        ],
        "notes": "Grocery taxed at reduced 4% state rate. High combined rate.",
    },
    "TX": {
        "name": "Texas",
        "base_rate": 0.0625,
        "has_local": True,
        "max_local": 0.02,
        "avg_combined": 0.0820,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.PRESCRIPTION_DRUG,
            ExemptionCategory.MEDICAL_DEVICE,
        ],
        "locals": [
            LocalRate("Houston", "Harris", 0.02),
            LocalRate("Dallas", "Dallas", 0.02),
            LocalRate("Austin", "Travis", 0.02),
            LocalRate("San Antonio", "Bexar", 0.02),
            LocalRate("Fort Worth", "Tarrant", 0.02),
        ],
        "notes": "Origin-based. Max combined rate capped at 8.25%.",
    },
    "UT": {
        "name": "Utah",
        "base_rate": 0.0485,
        "has_local": True,
        "max_local": 0.04,
        "avg_combined": 0.0719,
        "exemptions": [ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Salt Lake City", "Salt Lake", 0.0235),
            LocalRate("Provo", "Utah", 0.0225),
        ],
        "notes": "Grocery taxed at reduced 3% combined rate.",
    },
    "VT": {
        "name": "Vermont",
        "base_rate": 0.06,
        "has_local": True,
        "max_local": 0.01,
        "avg_combined": 0.0624,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.CLOTHING,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [
            LocalRate("Burlington", "Chittenden", 0.01),
        ],
        "notes": "Destination-based. Local option tax 1%.",
    },
    "VA": {
        "name": "Virginia",
        "base_rate": 0.043,
        "has_local": True,
        "max_local": 0.017,
        "avg_combined": 0.0575,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Virginia Beach", "Virginia Beach", 0.017),
            LocalRate("Richmond", "Richmond City", 0.017),
            LocalRate("Norfolk", "Norfolk", 0.017),
        ],
        "notes": "Destination-based. Grocery taxed at reduced 1% rate.",
    },
    "WA": {
        "name": "Washington",
        "base_rate": 0.065,
        "has_local": True,
        "max_local": 0.04,
        "avg_combined": 0.0929,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Seattle", "King", 0.0375),
            LocalRate("Tacoma", "Pierce", 0.028),
            LocalRate("Spokane", "Spokane", 0.024),
        ],
        "notes": "Destination-based. High combined rates.",
    },
    "WV": {
        "name": "West Virginia",
        "base_rate": 0.06,
        "has_local": True,
        "max_local": 0.01,
        "avg_combined": 0.0652,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Charleston", "Kanawha", 0.01),
        ],
        "notes": "Destination-based. Municipal B&O tax also applies.",
    },
    "WI": {
        "name": "Wisconsin",
        "base_rate": 0.05,
        "has_local": True,
        "max_local": 0.0175,
        "avg_combined": 0.0543,
        "exemptions": [
            ExemptionCategory.GROCERY,
            ExemptionCategory.PRESCRIPTION_DRUG,
        ],
        "locals": [
            LocalRate("Milwaukee", "Milwaukee", 0.0175),
            LocalRate("Madison", "Dane", 0.005),
        ],
        "notes": "Destination-based. County tax 0.5%, stadium tax in select areas.",
    },
    "WY": {
        "name": "Wyoming",
        "base_rate": 0.04,
        "has_local": True,
        "max_local": 0.04,
        "avg_combined": 0.0536,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [
            LocalRate("Cheyenne", "Laramie", 0.01),
            LocalRate("Casper", "Natrona", 0.015),
        ],
        "notes": "Destination-based.",
    },
    "DC": {
        "name": "District of Columbia",
        "base_rate": 0.06,
        "has_local": False,
        "max_local": 0.0,
        "avg_combined": 0.06,
        "exemptions": [ExemptionCategory.GROCERY, ExemptionCategory.PRESCRIPTION_DRUG],
        "locals": [],
        "notes": "Single jurisdiction. 10% on meals, 10.25% on liquor.",
    },
}


class TaxRateDatabase:
    """
    Queryable database of state and local sales tax rates.

    Provides lookup by state code, jurisdiction, and exemption category.
    """

    def __init__(self) -> None:
        self._states: dict[str, StateRate] = {}
        self._load_rates()

    def _load_rates(self) -> None:
        for code, data in _STATE_DATA.items():
            state = StateRate(
                state_code=code,
                state_name=data["name"],
                base_rate=data["base_rate"],
                has_local_taxes=data["has_local"],
                max_local_rate=data["max_local"],
                avg_combined_rate=data["avg_combined"],
                exemptions=data["exemptions"],
                local_rates=data.get("locals", []),
                notes=data.get("notes", ""),
            )
            self._states[code] = state

    @property
    def state_count(self) -> int:
        return len(self._states)

    def get_state(self, state_code: str) -> Optional[StateRate]:
        """Retrieve full rate profile for a state."""
        return self._states.get(state_code.upper())

    def get_base_rate(self, state_code: str) -> float:
        """Return the base state sales tax rate (decimal)."""
        state = self.get_state(state_code)
        if state is None:
            raise ValueError(f"Unknown state code: {state_code}")
        return state.base_rate

    def get_combined_rate(
        self, state_code: str, city: Optional[str] = None
    ) -> float:
        """
        Return combined state + local rate.

        If a city is provided and found, uses that city's local rate.
        Otherwise falls back to the state average combined rate.
        """
        state = self.get_state(state_code)
        if state is None:
            raise ValueError(f"Unknown state code: {state_code}")

        if city:
            for local in state.local_rates:
                if local.jurisdiction.lower() == city.lower():
                    return state.base_rate + local.rate
        return state.avg_combined_rate

    def get_local_rate(
        self, state_code: str, city: str
    ) -> Optional[LocalRate]:
        """Look up a specific local jurisdiction rate."""
        state = self.get_state(state_code)
        if state is None:
            return None
        for local in state.local_rates:
            if local.jurisdiction.lower() == city.lower():
                return local
        return None

    def is_exempt(
        self, state_code: str, category: ExemptionCategory
    ) -> bool:
        """Check if a category is exempt from sales tax in a state."""
        state = self.get_state(state_code)
        if state is None:
            raise ValueError(f"Unknown state code: {state_code}")
        return category in state.exemptions

    def no_sales_tax_states(self) -> list[str]:
        """Return list of state codes with no state-level sales tax."""
        return [
            code
            for code, state in self._states.items()
            if state.base_rate == 0.0
        ]

    def states_exempting(self, category: ExemptionCategory) -> list[str]:
        """Return state codes that exempt a given category."""
        return [
            code
            for code, state in self._states.items()
            if category in state.exemptions
        ]

    def all_states(self) -> list[StateRate]:
        """Return all state rate profiles sorted by code."""
        return [self._states[k] for k in sorted(self._states)]

    def highest_rate_states(self, n: int = 10) -> list[StateRate]:
        """Return the N states with highest average combined rate."""
        return sorted(
            self._states.values(),
            key=lambda s: s.avg_combined_rate,
            reverse=True,
        )[:n]

    def lowest_rate_states(self, n: int = 10) -> list[StateRate]:
        """Return the N states with lowest nonzero average combined rate."""
        taxed = [s for s in self._states.values() if s.base_rate > 0]
        return sorted(taxed, key=lambda s: s.avg_combined_rate)[:n]
