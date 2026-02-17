"""
ChEMBL Drug API Service
Fetches drug details from ChEMBL database for drugs not found in local dataset
"""

import requests
import logging

logger = logging.getLogger(__name__)

def get_drug_from_chembl(drug_name):
    """
    Fetch drug details from ChEMBL API.
    Used as fallback when drug is not in local database.
    """
    base_url = "https://www.ebi.ac.uk/chembl/api/data"
    
    try:
        # Step 1 — Search for drug by name
        search_url = f"{base_url}/molecule/search?q={drug_name}"
        search_res = requests.get(search_url, timeout=15)
        search_res.raise_for_status()
        search_data = search_res.json()

        if search_data.get("page_meta", {}).get("total_count", 0) == 0:
            logger.info(f"[ChEMBL] No drug found for: {drug_name}")
            return None

        # Pick the first matching result
        chembl_id = search_data["molecules"][0]["molecule_chembl_id"]
        logger.info(f"[ChEMBL] Found {drug_name} -> {chembl_id}")

        # Step 2 — Get molecule details
        mol_url = f"{base_url}/molecule/{chembl_id}"
        mol_data = requests.get(mol_url, timeout=15).json()

        # Extract SMILES + basic properties
        smiles = mol_data.get("molecule_structures", {}).get("canonical_smiles")
        props = mol_data.get("molecule_properties", {}) or {}

        logP = props.get("cx_logp")
        logD = props.get("cx_logd")
        psa = props.get("psa")

        # Step 3 — Fetch mechanism / targets
        mech_url = f"{base_url}/mechanism?molecule_chembl_id={chembl_id}"
        mech_data = requests.get(mech_url, timeout=15).json()

        moa = None
        targets = []
        target_types = []
        organisms = []

        if mech_data.get("page_meta", {}).get("total_count", 0) > 0:
            for m in mech_data.get("mechanisms", []):
                if m.get("mechanism_of_action") and not moa:
                    moa = m.get("mechanism_of_action")
                if m.get("target_chembl_id"):
                    targets.append(m.get("target_chembl_id"))
                if m.get("target_type"):
                    target_types.append(m.get("target_type"))
                if m.get("organism"):
                    organisms.append(m.get("organism"))

        # Step 4 — Fetch activity (IC50 / pIC50)
        act_url = f"{base_url}/activity?molecule_chembl_id={chembl_id}&limit=50"
        act_data = requests.get(act_url, timeout=15).json()

        IC50 = None
        pIC50 = None

        for a in act_data.get("activities", []):
            if a.get("standard_type") in ["IC50", "Potency"]:
                IC50 = a.get("standard_value")
                pIC50 = a.get("pchembl_value")
                break  # Get first available

        # Step 5 — Create output matching local database format
        max_phase = mol_data.get("max_phase")
        
        result = {
            "drug_id": chembl_id,
            "drug_name": drug_name.upper(),
            "SMILES": smiles,
            "logD": float(logD) if logD else None,
            "logP": float(logP) if logP else None,
            "psa": float(psa) if psa else None,
            "solubility": _assess_solubility(logP, logD, psa),
            "drug_likeness": "Yes" if max_phase else "Unknown",
            "max_phase": max_phase,
            "IC50": IC50,
            "pIC50": pIC50,
            "target": ", ".join([t for t in targets if t]) or None,
            "organism": ", ".join([o for o in organisms if o]) or None,
            "target_type": ", ".join([tt for tt in target_types if tt]) or None,
            "mechanism_of_action": moa,
            "efo_term": None,
            "mesh_heading": None,
            "toxicity_alert": None,
            "source": "ChEMBL"  # Mark as external source
        }
        
        logger.info(f"[ChEMBL] Successfully fetched data for {drug_name}")
        return result

    except requests.exceptions.Timeout:
        logger.warning(f"[ChEMBL] Timeout while fetching {drug_name}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"[ChEMBL] Request error for {drug_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"[ChEMBL] Error fetching {drug_name}: {e}")
        return None


def _assess_solubility(logP, logD, psa):
    """Assess solubility based on molecular properties"""
    try:
        if logP is None or logD is None or psa is None:
            return 'Unknown'
        logP = float(logP)
        logD = float(logD)
        psa = float(psa)
        if logP < 3 and logD < 3 and psa > 75:
            return 'Good'
        elif logP < 5 and logD < 5 and psa > 50:
            return 'Moderate'
        else:
            return 'Poor'
    except Exception:
        return 'Unknown'


# Test function
if __name__ == "__main__":
    drug = input("Enter drug name: ")
    result = get_drug_from_chembl(drug)
    if result:
        import json
        print(json.dumps(result, indent=2))
    else:
        print("Drug not found in ChEMBL")

