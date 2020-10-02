import pandas as pd
import names
import numpy as np

def load_tutors_from_excel(filename):
    xl_file = pd.ExcelFile(filename)
    df_tutors_raw = {sheet_name: xl_file.parse(sheet_name) 
          for sheet_name in xl_file.sheet_names}["Feuil1"]
    return df_tutors_raw

def load_students_from_excel(filename):
    xl_file = pd.ExcelFile(filename)
    df_students = {sheet_name: xl_file.parse(sheet_name, header=2) 
          for sheet_name in xl_file.sheet_names}['Inscription option 2']
    return df_students

def hour2float(hour):
    try:
        h, m, s = str(hour).split(":")
    except:
        return 0
    return float(h)+float(m)/60

def float2hour(f):
    return f"{int(f//1)}:{int((f-f//1)*60):02d}"

def hour2float_tutors(hour):
    hour = hour[1:]
    try:
        h, m = str(hour).split("h")
    except:
        return 0
    return float(h)+float(m)/60

def generate_fake_entries(num=100):

    data = []
    def fake_entry():
        sc = np.array([1,0,0])
        np.random.shuffle(sc)
        
        subjects = np.array([0,0,0,0,0,1,2,3])
        np.random.shuffle(subjects)
        
        dispos =  {}
        part_of_days = ["midi", "soir"]
        days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
        for day in days:
            for part_of_day in part_of_days:
                if np.random.random()<0.99:
                    t0 = np.random.random()*6+11
                    t1 = t0+2
                    dispos[f"{day} {part_of_day}"] = [t0, t1]
        
        return {"school": sc,
               "nom": names.get_full_name(),
               "subjects": subjects,
               "dispo": dispos}
    
    # Add fake tutors
    for i in range(num):
        data.append(fake_entry())
    return data


def clean_tutors_df(df):
    
    # Subjects
    columns = ["Français",
               "Anglais", 
               "Espagnol", 
               "Mathématiques", 
               "Sciences",
               "Histoire/Géographie", 
               "Chimie",
               "Physique",
               "Autre matière"]
    for column in columns:
        df[column] = df[column].replace("PasDuTout", value=0)
        df[column] = df[column].replace("Partiellement", value=1)
        df[column] = df[column].replace("Tres", value=2)
    
    # Schools
    columns = ["Vanier",
               "Camaradière", 
               "Charlesbourg"]
    for column in columns:
        df[column] = df[column].replace("NonDisponible", value=0)
        df[column] = df[column].replace("Disponible", value=1)
        df[column] = df[column].replace("Prioritaire", value=2)

    # Dispos
    keys = ["(début)", "(fin)"]
    part_of_days = ["midi", "soir"]
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
    all_dispos = []
    for key,row in df.iterrows():
        dispos = {}
        for day in days:
            for part_of_day in part_of_days:
                try:
                    key1 = f"{day} {part_of_day} {keys[0]}"
                    key2 = f"{day} {part_of_day} {keys[1]}"
                    d1, d2 = row[key1], row[key2]
                except:
                    continue
                
                df[f"{day} {part_of_day} {keys[0]}"] = d1
                df[f"{day} {part_of_day} {keys[1]}"] = d2    
                
                if pd.isna(d1) or pd.isna(d2):
                    continue
                
                if d1==0 or d2==0:
                    continue
                
                if hour2float_tutors(d1)!=0 or hour2float_tutors(d2)!=0:
                    dispos[f"{day} {part_of_day}".lower()] = (hour2float_tutors(d1), hour2float_tutors(d2))
        all_dispos.append(dispos)
        
    df["dispos"] = all_dispos

    return df

def sanitize_tutors_df(df):

    subjects = ["Français",
               "Anglais", 
               "Espagnol", 
               "Mathématiques", 
               "Sciences",
                "Physique",
                "Chimie",
               "Histoire/Géographie"]
    schools = ["Vanier",
               "Camaradière", 
               "Charlesbourg"]
    data = []

    for index, row in df.iterrows():
        data.append({"school": np.array([row[s] for s in schools]),
                     "nom": row["Prénom Nom"],
                      "subjects": np.array([(0 if pd.isna(row[s]) else row[s]) for s in subjects]),
                     "dispo": row["dispos"]})
    
    return pd.DataFrame(data)

def clean_students_df(df):
    
    # Subjects
    columns = ["Fr", "Ang", "Esp", "Maths", "Sci", "Phy", "Chi", "Hist/Géo"]
    for column in columns:
        df[column] = df[column].fillna(value=0)
    
    # School
    column = "École secondaire fréquentée"
    replace_keys = {"École secondaire Vanier": "Vanier",
                    "École secondaire La Camaradière": "Camaradiere",
                    "Polyvalente de Charlesbourg": "Charlesbourg",
                   }
    for key, val in replace_keys.items():
        df[column] = df[column].replace(key, value=val)
    
    # Dispo
    keys = ["DE", "À"]
    part_of_days = ["midi", "soir"]
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
    all_dispos = []
    for key,row in df.iterrows():
        dispos = {}
        for day in days:
            for part_of_day in part_of_days:
                key1 = f"{day} {part_of_day} {keys[0]}"
                key2 = f"{day} {part_of_day} {keys[1]}"
                d1, d2 = row[key1], row[key2]
                if pd.isna(d1) or pd.isna(d2):
                    continue
                
                dispos[f"{day} {part_of_day}".lower()] = (hour2float(d1), hour2float(d2))
        all_dispos.append(dispos)
    df["dispos"] = all_dispos
    

    subjects = ["Fr", "Ang", "Esp", "Maths", "Sci", "Phy", "Chi", "Hist/Géo"]
    schools = ["Vanier",
               "Camaradiere", 
               "Charlesbourg"]
    data = []
    for index, row in df.iterrows():
        data.append({"school": np.array([float(row["École secondaire fréquentée"]==s) for s in schools]),
                     "nom": row["Prénom et nom de l'ÉA"],
                     "subjects": np.array([row[s] for s in subjects]),
                     "dispo": row["dispos"]})


    return pd.DataFrame(data)