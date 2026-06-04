"""Florida county configuration — name, DOR number, and property appraiser URL."""

FL_COUNTIES = [
    # (name, dor_number, pa_website)
    ("Alachua", 11, "https://www.acpafl.org"),
    ("Baker", 12, "https://www.bakerpa.com"),
    ("Bay", 13, "https://www.baypa.net"),
    ("Bradford", 14, "https://www.bradfordtaxcollector.com"),
    ("Brevard", 15, "https://www.bcpao.us"),
    ("Broward", 16, "https://bcpa.net"),
    ("Calhoun", 17, "https://www.calhounpa.com"),
    ("Charlotte", 18, "https://www.ccappraiser.com"),
    ("Citrus", 19, "https://www.citruspa.org"),
    ("Clay", 20, "https://www.ccpao.com"),
    ("Collier", 21, "https://www.collierappraiser.com"),
    ("Columbia", 22, "https://www.columbiapa.com"),
    ("Dade", 23, "https://www.miamidade.gov/pa"),
    ("DeSoto", 24, "https://www.desotopa.com"),
    ("Dixie", 25, "https://www.dixiepa.com"),
    ("Duval", 26, "https://www.duvalpa.com"),
    ("Escambia", 27, "https://www.escpa.org"),
    ("Flagler", 28, "https://www.flaglerpa.com"),
    ("Franklin", 29, "https://www.franklinpa.com"),
    ("Gadsden", 30, "https://www.gadsdenpa.com"),
    ("Gilchrist", 31, "https://www.gilchristpa.com"),
    ("Glades", 32, "https://www.gladespa.com"),
    ("Gulf", 33, "https://www.gulfpa.com"),
    ("Hamilton", 34, "https://www.hamiltonpa.com"),
    ("Hardee", 35, "https://www.hardeepa.com"),
    ("Hendry", 36, "https://www.hendrypa.com"),
    ("Hernando", 37, "https://www.hernandocounty.us/pa"),
    ("Highlands", 38, "https://www.highlandspa.com"),
    ("Hillsborough", 39, "https://www.hcpafl.org"),
    ("Holmes", 40, "https://www.holmespa.com"),
    ("Indian River", 41, "https://www.ircpa.org"),
    ("Jackson", 42, "https://www.jacksonpa.com"),
    ("Jefferson", 43, "https://www.jeffersonpa.com"),
    ("Lafayette", 44, "https://www.lafayettepa.com"),
    ("Lake", 45, "https://www.lakecopropappr.com"),
    ("Lee", 46, "https://www.leepa.org"),
    ("Leon", 47, "https://www.leonpa.org"),
    ("Levy", 48, "https://www.levypa.com"),
    ("Liberty", 49, "https://www.libertypa.com"),
    ("Madison", 50, "https://www.madisonpa.com"),
    ("Manatee", 51, "https://www.manateepa.com"),
    ("Marion", 52, "https://www.pa.marion.fl.us"),
    ("Martin", 53, "https://www.pa.martin.fl.us"),
    ("Monroe", 54, "https://www.monroecounty-fl.gov/pa"),
    ("Nassau", 55, "https://www.nassauflpa.com"),
    ("Okaloosa", 56, "https://www.okaloosapa.com"),
    ("Okeechobee", 57, "https://www.okeechobeepa.com"),
    ("Orange", 58, "https://www.ocpafl.org"),
    ("Osceola", 59, "https://www.osceolapa.org"),
    ("Palm Beach", 60, "https://www.pbcgov.org/papa"),
    ("Pasco", 61, "https://www.pascopa.com"),
    ("Pinellas", 62, "https://www.pcpao.org"),
    ("Polk", 63, "https://www.polkpa.org"),
    ("Putnam", 64, "https://www.putnampa.com"),
    ("St. Johns", 65, "https://www.sjcpa.us"),
    ("St. Lucie", 66, "https://www.paslc.gov"),
    ("Santa Rosa", 67, "https://www.santarosapa.gov"),
    ("Sarasota", 68, "https://www.sc-pa.com"),
    ("Seminole", 69, "https://www.scpafl.org"),
    ("Sumter", 70, "https://www.sumterpa.com"),
    ("Suwannee", 71, "https://www.suwannepa.com"),
    ("Taylor", 72, "https://www.taylorpa.com"),
    ("Union", 73, "https://www.unionpa.com"),
    ("Volusia", 74, "https://www.volusia.org/pa"),
    ("Wakulla", 75, "https://www.wakullapa.com"),
    ("Walton", 76, "https://www.waltonpa.com"),
    ("Washington", 77, "https://www.washingtonpa.com"),
]

# State data portal base URL
FL_DOR_BASE = "https://floridarevenue.com/property/dataportal/Documents/PTO%20Data%20Portal"

# Data types available
DATA_TYPES = {
    "nal": "NAL",     # Name-Address-Legal (tax roll)
    "sdf": "SDF",     # Sales Data File
    "nap": "NAP",     # Name-Address-Property (tangible personal property)
}

# Current tax year folder
TAX_YEAR = "2025F"  # 2025 Final
