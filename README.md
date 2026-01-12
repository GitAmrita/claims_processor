# claims_processor
## Sample Claim Validation Results

The table below lists which claims fail which validations according to the business rules:


| Claim ID | Failing Validations |
|----------|-------------------|
| CLM001 | ✅ Passes all |
| CLM002 | ✅ Passes all |
| CLM003 | ✅ Passes all |
| CLM004 | member_id invalid, ndc fails OpenFDA |
| CLM005 | quantity = 0 |
| CLM006 | days_supply = 100 |
| CLM007 | quantity = -5, days_supply = 0 |
| CLM008 | drug_cost = 0 |
| CLM009 | date_of_service future, drug_cost = -20 |
| CLM010 | ndc fails OpenFDA |
| CLM011 | ndc fails OpenFDA |
| CLM012 | ✅ Passes all |
| CLM013 | Too many pills |
| CLM014 | Too many pills|
| CLM015 | member_id invalid, ndc fails OpenFDA |
| CLM016 | ndc invalid length, date_of_service future |
| CLM017 | drug_cost = 0 |
| CLM018 | date_of_service future, days_supply = 0 |
| CLM019 | Too many pills |
| CLM020 | ✅ Passes all |
| CLM021 | member_id missing |
| CLM022 | ndc missing |
| CLM023 | date_of_service missing |
| CLM024 | days_supply missing |
| CLM025 | drug_cost missing |
| CLM026 | plan_type missing, ndc fails OpenFDA |

