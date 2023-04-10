

def remove_duplicates(data):
    seen = set()
    new_data = []
    for item in data:
        # Convertimos cada item a una tupla y comprobamos si ya se ha visto antes
        item_tuple = tuple(sorted(item.items()))
        if item_tuple not in seen:
            new_data.append(item)
            seen.add(item_tuple)
    return new_data