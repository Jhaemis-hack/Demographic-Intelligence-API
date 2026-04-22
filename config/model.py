def create_profile(data):
    return {
        "id": data["id"],
        "name": data["name"],
        "gender": data["gender"],
        "gender_probability": data["gender_probability"],
        "age": data["age"],
        "age_group": data["age_group"],
        "country_id": data["country_id"],
        "country_name": data["country_name"],
        "country_probability": data["country_probability"],
        "created_at": data["created_at"],
    }


def create_profile_list_item(data):
    return {
        "id": data["id"],
        "name": data["name"],
        "gender": data["gender"],
        "gender_probability": data["gender_probability"],
        "age": data["age"],
        "age_group": data["age_group"],
        "country_id": data["country_id"],
        "country_name": data["country_name"],
        "country_probability": data["country_probability"],
        "created_at": data["created_at"],
    }


def extract_gender(genderize, nationalize, agify):
    return {
        "name": genderize["name"],
        "gender": genderize["gender"],
        "gender_probability": genderize["gender_probability"],
        "sample_size": genderize["sample_size"],
        "age": agify["age"],
        "age_group": agify["age_group"],
        "country_id": nationalize["country_id"],
        "country_probability": nationalize["country_probability"],
    }
