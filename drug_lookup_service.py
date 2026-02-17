"""
Multi-source Drug Lookup Service
Combines PubChem, DrugCentral, RxNorm, and ChEMBL APIs for comprehensive drug information
"""

import requests
import logging
import urllib3
from chembl_service import get_drug_from_chembl

# Suppress SSL warnings for DrugCentral (certificate issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# ============== RxNorm API - Drug Name Normalization ==============

def normalize_drug_name(drug_name):
    """
    Normalize drug name using RxNorm API.
    Handles synonyms like paracetamol = acetaminophen
    """
    try:
        # First try approximate match
        url = f"https://rxnav.nlm.nih.gov/REST/approximateTerm.json?term={drug_name}&maxEntries=1"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        candidates = data.get("approximateGroup", {}).get("candidate", [])
        if candidates:
            rxcui = candidates[0].get("rxcui")
            normalized_name = candidates[0].get("name", drug_name)
            logger.info(f"[RxNorm] Normalized '{drug_name}' -> '{normalized_name}' (RXCUI: {rxcui})")
            return normalized_name, rxcui
        
        # Fallback: try exact spelling suggestions
        url2 = f"https://rxnav.nlm.nih.gov/REST/spellingsuggestions.json?name={drug_name}"
        resp2 = requests.get(url2, timeout=10)
        data2 = resp2.json()
        
        suggestions = data2.get("suggestionGroup", {}).get("suggestionList", {}).get("suggestion", [])
        if suggestions:
            logger.info(f"[RxNorm] Suggestion for '{drug_name}': {suggestions[0]}")
            return suggestions[0], None
            
        return drug_name, None
        
    except Exception as e:
        logger.warning(f"[RxNorm] Error normalizing {drug_name}: {e}")
        return drug_name, None


# ============== PubChem API ==============

def get_drug_from_pubchem(drug_name):
    """Fetch drug details from PubChem API"""
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug_name}/JSON"
        resp = requests.get(url, timeout=15)
        
        if resp.status_code != 200:
            logger.info(f"[PubChem] Drug not found: {drug_name}")
            return None
            
        data = resp.json()
        props = data.get("PC_Compounds", [{}])[0]
        
        if not props:
            return None
        
        # Extract CID
        cid = props.get("id", {}).get("id", {}).get("cid")
        
        # Extract SMILES and other properties
        smiles = None
        iupac_name = None
        molecular_formula = None
        molecular_weight = None
        
        for p in props.get("props", []):
            urn = p.get("urn", {})
            label = urn.get("label", "")

            # Accept any SMILES (Canonical, Absolute, or Connectivity)
            if label == "SMILES" and not smiles:
                smiles = p.get("value", {}).get("sval")
            elif label == "IUPAC Name" and (urn.get("name") == "Preferred" or not iupac_name):
                iupac_name = p.get("value", {}).get("sval")
            elif label == "Molecular Formula":
                molecular_formula = p.get("value", {}).get("sval")
            elif label == "Molecular Weight":
                molecular_weight = p.get("value", {}).get("fval")
        
        # Get additional properties (logP, PSA) from property endpoint
        logP, psa = None, None
        try:
            prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/XLogP,TPSA/JSON"
            prop_resp = requests.get(prop_url, timeout=10)
            if prop_resp.status_code == 200:
                prop_data = prop_resp.json()
                prop_list = prop_data.get("PropertyTable", {}).get("Properties", [{}])[0]
                logP = prop_list.get("XLogP")
                psa = prop_list.get("TPSA")
        except Exception:
            pass
        
        result = {
            "drug_id": f"CID{cid}",
            "drug_name": drug_name.upper(),
            "SMILES": smiles,
            "logD": None,
            "logP": logP,
            "psa": psa,
            "solubility": _assess_solubility(logP, None, psa),
            "drug_likeness": "Unknown",
            "max_phase": None,
            "IC50": None,
            "pIC50": None,
            "target": None,
            "organism": None,
            "target_type": None,
            "mechanism_of_action": None,
            "iupac_name": iupac_name,
            "molecular_formula": molecular_formula,
            "molecular_weight": molecular_weight,
            "efo_term": None,
            "mesh_heading": None,
            "toxicity_alert": None,
            "source": "PubChem"
        }
        
        logger.info(f"[PubChem] Found {drug_name} -> CID{cid}")
        return result
        
    except Exception as e:
        logger.error(f"[PubChem] Error fetching {drug_name}: {e}")
        return None


def _assess_solubility(logP, logD, psa):
    """Assess solubility based on molecular properties"""
    try:
        if logP is None and psa is None:
            return 'Unknown'
        logP = float(logP) if logP else 3
        logD = float(logD) if logD else logP
        psa = float(psa) if psa else 60
        if logP < 3 and logD < 3 and psa > 75:
            return 'Good'
        elif logP < 5 and logD < 5 and psa > 50:
            return 'Moderate'
        else:
            return 'Poor'
    except Exception:
        return 'Unknown'


# ============== DrugCentral API ==============

def get_drug_from_drugcentral(drug_name):
    """Fetch drug details from DrugCentral API - provides mechanism, targets, toxicity"""
    try:
        url = f"https://drugcentral.org/api/v1/drug?name={drug_name}"
        # Note: verify=False due to SSL certificate issues with drugcentral.org
        resp = requests.get(url, timeout=15, verify=False)

        if resp.status_code != 200:
            logger.info(f"[DrugCentral] Drug not found: {drug_name}")
            return None

        data = resp.json()

        if not data or (isinstance(data, list) and len(data) == 0):
            return None

        drug = data[0] if isinstance(data, list) else data

        # Extract information
        struct = drug.get("structure", {}) or {}

        result = {
            "drug_id": drug.get("id") or f"DC_{drug_name}",
            "drug_name": drug.get("name", drug_name).upper(),
            "SMILES": struct.get("smiles"),
            "logD": None,
            "logP": struct.get("alogp"),
            "psa": struct.get("polar_surface_area"),
            "solubility": _assess_solubility(struct.get("alogp"), None, struct.get("polar_surface_area")),
            "drug_likeness": "Yes" if drug.get("approved") else "Unknown",
            "max_phase": 4 if drug.get("approved") else None,
            "IC50": None,
            "pIC50": None,
            "target": None,
            "organism": "Homo sapiens",
            "target_type": None,
            "mechanism_of_action": drug.get("mechanism_of_action"),
            "efo_term": None,
            "mesh_heading": None,
            "toxicity_alert": drug.get("black_box_warning"),
            "indication": drug.get("indication"),
            "source": "DrugCentral"
        }

        # Get targets if available
        targets = drug.get("targets", [])
        if targets:
            target_names = [t.get("name", "") for t in targets[:5] if t.get("name")]
            result["target"] = ", ".join(target_names) if target_names else None
            target_types = [t.get("target_class", "") for t in targets[:5] if t.get("target_class")]
            result["target_type"] = ", ".join(set(target_types)) if target_types else None

        logger.info(f"[DrugCentral] Found {drug_name}")
        return result

    except Exception as e:
        logger.error(f"[DrugCentral] Error fetching {drug_name}: {e}")
        return None


# ============== Interaction Checking (Hybrid) ==============

LOCAL_INTERACTIONS = {
    # --- Anticoagulant Interactions (Bleeding Risk) ---
    frozenset(['ASPIRIN', 'WARFARIN']): "CRITICAL: High risk of bleeding. Aspirin enhances the anticoagulant effect of Warfarin.",
    frozenset(['IBUPROFEN', 'WARFARIN']): "CRITICAL: Increased risk of bleeding due to inhibition of platelet aggregation and gastric irritation.",
    frozenset(['NAPROXEN', 'WARFARIN']): "CRITICAL: Significant risk of gastrointestinal bleeding.",
    frozenset(['APIXABAN', 'ASPIRIN']): "Increased risk of bleeding. Monitor specifically for signs of bleeding.",
    frozenset(['RIVAROXABAN', 'NSAIDS']): "Increased bleeding risk. Avoid concurrent use if possible.",
    frozenset(['CIPROFLOXACIN', 'WARFARIN']): "Warfarin effects may be increased (elevated INR), risk of bleeding.",
    frozenset(['ERYTHROMYCIN', 'WARFARIN']): "Increases Warfarin levels significantly via CYP450 inhibition. Monitor INR.",

    # --- Statin Interactions (Myopathy/Rhabdomyolysis) ---
    frozenset(['SIMVASTATIN', 'AMLODIPINE']): "Increased risk of myopathy/rhabdomyolysis. Limit Simvastatin dose to 20mg if used together.",
    frozenset(['SIMVASTATIN', 'AMIODARONE']): "High risk of muscle toxicity. Limit Simvastatin dose to 20mg.",
    frozenset(['SIMVASTATIN', 'VERAPAMIL']): "Increased risk of myopathy and rhabdomyolysis.",
    frozenset(['SIMVASTATIN', 'DILTIAZEM']): "Risk of prolonged exposure to Simvastatin. Dose limit required.",
    frozenset(['SIMVASTATIN', 'KETOCONAZOLE']): "CONTRAINDICATED: Severe risk of rhabdomyolysis.",
    frozenset(['SIMVASTATIN', 'CLARITHROMYCIN']): "CONTRAINDICATED: Strong CYP3A4 inhibition increases statin toxicity.",
    frozenset(['ATORVASTATIN', 'GEMFIBROZIL']): "Increased risk of muscle damage.",

    # --- Cardiovascular Interactions ---
    frozenset(['SILDENAFIL', 'NITROGLYCERIN']): "DANGEROUS: Risk of severe, potentially fatal hypotension. Do not use together.",
    frozenset(['TADALAFIL', 'ISOSORBIDE MONONITRATE']): "DANGEROUS: Severe hypotension risk. Contraindicated.",
    frozenset(['LISINOPRIL', 'POTASSIUM CHLORIDE']): "Risk of hyperkalemia (high blood potassium). Monitor levels.",
    frozenset(['LOSARTAN', 'SPIRONOLACTONE']): "Increased risk of hyperkalemia, especially in renal impairment.",
    frozenset(['DIGOXIN', 'AMIODARONE']): "Amiodarone increases Digoxin levels by up to 70%. Digoxin toxicity risk.",
    frozenset(['DIGOXIN', 'VERAPAMIL']): "Increases Digoxin serum concentrations. Monitor for toxicity.",
    frozenset(['CLONIDINE', 'PROPRANOLOL']): "Risk of severe rebound hypertension if Clonidine is withdrawn while on Beta-blocker.",

    # --- CNS / Serotonin Syndrome ---
    frozenset(['TRAMADOL', 'SERTRALINE']): "Risk of Serotonin Syndrome (confusion, agitation, rapid heart rate).",
    frozenset(['FLUOXETINE', 'PHENELZINE']): "CONTRAINDICATED: Serotonin Syndrome risk with SSRI + MAOI. Washout period required.",
    frozenset(['OXYCODONE', 'ALPRAZOLAM']): "DANGEROUS: Risk of profound sedation, respiratory depression, coma, and death.",
    frozenset(['MORPHINE', 'LORAZEPAM']): "DANGEROUS: Risk of respiratory depression and sedation.",
    frozenset(['AMITRIPTYLINE', 'TRANYLCYPROMINE']): "Significant risk of neurotoxicity and Serotonin Syndrome.",

    # --- Other Critical Interactions ---
    frozenset(['METHOTREXATE', 'TRIMETHOPRIM']): "Bone marrow suppression risk. Avoid concomitant use.",
    frozenset(['LITHIUM', 'LISINOPRIL']): "ACE Inhibitors can increase Lithium toxicity. Monitor levels.",
    frozenset(['LITHIUM', 'HYDROCHLOROTHIAZIDE']): "Diuretics reduce Lithium clearance, leading to toxicity.",
    frozenset(['THEOPHYLLINE', 'CIPROFLOXACIN']): "Increased Theophylline levels (seizure risk) due to enzyme inhibition.",
    frozenset(['COLCHICINE', 'CLARITHROMYCIN']): "Potential for fatal Colchicine toxicity, especially in renal impairment."
}

def check_interaction_between(rxcui1, rxcui2, name1=None, name2=None):
    """
    Check for drug-drug interactions using local list and RxNav API (if available).
    Returns a list of descriptions.
    """
    interactions = []
    
    # 1. Local Check (fast, reliable for common pairs)
    if name1 and name2:
        key = frozenset([name1.upper(), name2.upper()])
        if key in LOCAL_INTERACTIONS:
            logger.info(f"[Interaction] Found local interaction for {name1} + {name2}")
            interactions.append(LOCAL_INTERACTIONS[key])
            
    # 2. RxNav API Check (currently disabled/flaky, can be enabled if URL is fixed)
    # The endpoint /REST/interaction/list.json seems to be moved or requires special params.
    # We will skip it for now to avoid 404 errors.
    
    return interactions


def lookup_drug(drug_name):
    """
    Comprehensive drug lookup that searches ALL APIs and combines best data:
    1. First normalize name using RxNorm
    2. Search ALL APIs with both original and normalized name
    3. Merge results from all sources for best coverage
    """
    logger.info(f"[DrugLookup] Starting comprehensive lookup for: {drug_name}")

    # Step 1: Normalize drug name using RxNorm
    normalized_name, rxcui = normalize_drug_name(drug_name)
    names_to_try = [drug_name]
    if normalized_name.lower() != drug_name.lower():
        names_to_try.append(normalized_name)
        logger.info(f"[DrugLookup] Normalized '{drug_name}' -> '{normalized_name}'")

    # Step 2: Collect results from ALL APIs
    all_results = {
        'pubchem': None,
        'drugcentral': None,
        'chembl': None
    }

    sources_found = []

    for name in names_to_try:
        # Try PubChem (best for SMILES, structure)
        if not all_results['pubchem']:
            pubchem_result = get_drug_from_pubchem(name)
            if pubchem_result:
                all_results['pubchem'] = pubchem_result
                sources_found.append('PubChem')
                logger.info(f"[DrugLookup] Found in PubChem with name '{name}'")

        # Try DrugCentral (best for mechanism, targets, toxicity)
        if not all_results['drugcentral']:
            dc_result = get_drug_from_drugcentral(name)
            if dc_result:
                all_results['drugcentral'] = dc_result
                sources_found.append('DrugCentral')
                logger.info(f"[DrugLookup] Found in DrugCentral with name '{name}'")

        # Try ChEMBL (best for bioactivity data)
        if not all_results['chembl']:
            chembl_result = get_drug_from_chembl(name)
            if chembl_result:
                all_results['chembl'] = chembl_result
                sources_found.append('ChEMBL')
                logger.info(f"[DrugLookup] Found in ChEMBL with name '{name}'")

    # Step 3: Merge results - combine best data from each source
    if not any(all_results.values()):
        logger.warning(f"[DrugLookup] No results found for '{drug_name}'")
        return None

    merged = _merge_api_results(all_results, drug_name)
    merged["normalized_name"] = normalized_name
    merged["rxcui"] = rxcui
    merged["sources"] = sources_found
    merged["source"] = " + ".join(sources_found) if len(sources_found) > 1 else (sources_found[0] if sources_found else "Unknown")

    logger.info(f"[DrugLookup] Merged data from: {sources_found}")
    return merged


def _merge_api_results(results, original_name):
    """Merge results from multiple APIs, preferring non-null values"""
    merged = {
        "drug_id": None,
        "drug_name": original_name.upper(),
        "SMILES": None,
        "logD": None,
        "logP": None,
        "psa": None,
        "solubility": None,
        "drug_likeness": None,
        "max_phase": None,
        "IC50": None,
        "pIC50": None,
        "target": None,
        "organism": None,
        "target_type": None,
        "mechanism_of_action": None,
        "iupac_name": None,
        "molecular_formula": None,
        "molecular_weight": None,
        "efo_term": None,
        "mesh_heading": None,
        "toxicity_alert": None,
        "indication": None
    }

    # Priority order for each field (which API to prefer)
    field_priority = {
        # PubChem best for structure
        "SMILES": ['pubchem', 'chembl', 'drugcentral'],
        "logP": ['pubchem', 'drugcentral', 'chembl'],
        "psa": ['pubchem', 'drugcentral', 'chembl'],
        "iupac_name": ['pubchem', 'chembl', 'drugcentral'],
        "molecular_formula": ['pubchem', 'chembl', 'drugcentral'],
        "molecular_weight": ['pubchem', 'chembl', 'drugcentral'],

        # DrugCentral best for pharmacology
        "mechanism_of_action": ['drugcentral', 'chembl', 'pubchem'],
        "target": ['drugcentral', 'chembl', 'pubchem'],
        "target_type": ['drugcentral', 'chembl', 'pubchem'],
        "toxicity_alert": ['drugcentral', 'chembl', 'pubchem'],
        "indication": ['drugcentral', 'chembl', 'pubchem'],

        # ChEMBL best for bioactivity
        "IC50": ['chembl', 'drugcentral', 'pubchem'],
        "pIC50": ['chembl', 'drugcentral', 'pubchem'],
        "max_phase": ['chembl', 'drugcentral', 'pubchem'],
        "drug_likeness": ['chembl', 'drugcentral', 'pubchem'],

        # General fields
        "drug_id": ['chembl', 'pubchem', 'drugcentral'],
        "drug_name": ['drugcentral', 'chembl', 'pubchem'],
        "organism": ['chembl', 'drugcentral', 'pubchem'],
        "efo_term": ['chembl', 'drugcentral', 'pubchem'],
        "mesh_heading": ['chembl', 'drugcentral', 'pubchem'],
        "logD": ['chembl', 'drugcentral', 'pubchem'],
        "solubility": ['pubchem', 'drugcentral', 'chembl']
    }

    # Merge fields based on priority
    for field, priority_order in field_priority.items():
        for source in priority_order:
            if results.get(source) and results[source].get(field):
                value = results[source][field]
                if value and value != 'N/A' and value != 'Unknown':
                    merged[field] = value
                    break

    # Ensure drug_name is set properly
    if not merged["drug_name"] or merged["drug_name"] == "UNKNOWN":
        for source in ['drugcentral', 'pubchem', 'chembl']:
            if results.get(source) and results[source].get('drug_name'):
                merged["drug_name"] = results[source]['drug_name']
                break
        if not merged["drug_name"]:
            merged["drug_name"] = original_name.upper()

    return merged


# Test
if __name__ == "__main__":
    import json
    test_drugs = ["paracetamol", "aspirin", "ibuprofen", "metformin"]
    for drug in test_drugs:
        print(f"\n{'='*50}")
        print(f"Looking up: {drug}")
        result = lookup_drug(drug)
        if result:
            print(json.dumps(result, indent=2, default=str))
        else:
            print("Not found")

