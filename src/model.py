import logging
import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

from utils import float2hour

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("dam-logger")

def pair_students(df_students, df_tutors, w_paired=1):

    students_index = df_students.index.tolist()
    tutor_index = df_tutors.index.tolist()
    num_tutors = len(tutor_index)
    num_students = len(students_index)

    model = cp_model.CpModel()


    # Verify a match goes to the same school
    def same_school(kid, tutor):
        return ((df_students.loc[kid].school*df_tutors.loc[tutor].school)).sum()>0

     # Verify the tutor teaches at least one required subject
    def overlap_subjects(kid, tutor):
        a = np.array(df_students.loc[kid].subjects)
        b = np.array(df_tutors.loc[tutor].subjects)
        return ((a*b)>0).sum()>0

    # Verify at least one match in schedule
    def overlap_dispos(kid, tutor, session=1):
        k = df_students.loc[kid].dispo
        t = df_tutors.loc[tutor].dispo
        for key,item in k.items():
            if key in t:
                t1, t2 = t[key]
                t1k, t2k = item
                if min(t2, t2k)-max(t1, t1k)>=session:
                    return True
        return False   

    def hard_constraints(kid, tutor):
        return overlap_dispos(kid, tutor) and overlap_subjects(kid, tutor) and same_school(kid, tutor)

    # Apply hard constraints
    shifts = {}
    for tutor in df_tutors.index.tolist():
        n=0
        for kid in df_students.index.tolist():
            if hard_constraints(kid, tutor):
                shifts[(kid, tutor)] = model.NewBoolVar('shift_k%i__t%i' % (kid, tutor))
                n+=1
        if n==0:
            logger.warning(f"{df_tutors.loc[tutor].nom} ({tutor}) can't be matched.")
    logger.info(f"{len(shifts)} possible edges.")


    # Maximum number of student per tutor
    def tutor_can_only_have_n_match(tutor, n_max=1):
        return sum(shifts[(kid, tutor)] for kid in students_index if (kid,tutor) in shifts)<=n_max

    for tutor in tutor_index:
        model.Add(tutor_can_only_have_n_match(tutor))

    # Each student has exactly one tutor
    def student_are_assigned_to_one_tutor(kid):
        return (sum(shifts[(kid, tutor)] for tutor in tutor_index if (kid,tutor) in shifts)<=1)

    for kid in students_index:
        model.Add(student_are_assigned_to_one_tutor(kid))

    
    # Maximize the quality of matching subjects
    def overlap_subjects_quality(kid, tutor):
        a = np.array(df_students.loc[kid].subjects)
        b = np.array(df_tutors.loc[tutor].subjects)
        return shifts[(kid, tutor)]*int((a*b).sum())

    # Maximize the quality of matching schools
    def same_school_quality(kid, tutor):
        return ((df_students.loc[kid].school*df_tutors.loc[tutor].school)).sum()*shifts[(kid, tutor)]

    # Total quality
    def quality(kid, tutor):
        return overlap_subjects_quality(kid, tutor) + same_school_quality(kid, tutor) + w_paired*shifts[(kid, tutor)]

    # Maximize the quality
    model.Maximize(sum(quality(*s) for s in shifts))

    # Solve
    logger.info("Solving.")
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    logger.info("Solving completed.")

    logger.info('  - Number of shift requests met = %i' % solver.ObjectiveValue())
    logger.info('  - wall time       : %f s' % solver.WallTime())

    if status == cp_model.OPTIMAL:
        logger.info("An optimal feasible solution was found.")
    if status == cp_model.FEASIBLE:
        logger.info("A feasible solution was found, but we don't know if it's optimal.")
    if status == cp_model.INFEASIBLE:
        logger.info("The problem was proven infeasible.")
        return False, None, None
    if status == cp_model.MODEL_INVALID:
        logger.info("The given CpModelProto didn't pass the validation step. You can get a detailed error by calling ValidateCpModel(model_proto).")
        return False, None, None
    if status == cp_model.UNKNOWN:
        logger.info("The status of the model is unknown because no solution was found (or the problem was not proven INFEASIBLE) before something caused the solver to stop, such as a time limit, a memory limit, or a custom limit set by the user.")
        return False, None, None

    return True, solver, shifts



class SolutionPrettyfier():

    def __init__(self, df_students, df_tutors, solver, shifts):
        self.df_tutors = df_tutors
        self.df_students = df_students
        self.solver = solver
        self.shifts = shifts
        self.accepted_shifts = self.get_accepted_solution() 
        return

    def get_accepted_solution(self):
        accepted_shifts = []
        for tutor in self.df_tutors.index.tolist():
            for kid in self.df_students.index.tolist():
                if (kid, tutor) in self.shifts:
                    if self.solver.Value(self.shifts[(kid, tutor)]):
                        accepted_shifts.append((kid, tutor))
        return accepted_shifts


    def find_matching_subjects(self, kid, tutor, no_tutor=False):
        subjects = ["Français", 
                        "Anglais", 
                        "Espagnol", 
                        "Mathématiques", 
                        "Sciences", 
                        "Physique", 
                        "Chimie", 
                        "Hist-Geo"]
            
        def f_sub(i):
            need = ["-", "+", "++", "+++"]
            if no_tutor:
                return subjects[i]+" ("+need[int(self.df_students.loc[kid].subjects[i])]+")"
            return subjects[i]+" ("+need[int(self.df_students.loc[kid].subjects[i])]+", "+need[int(self.df_tutors.loc[tutor].subjects[i])] +")"
        
        prefs = self.df_students.loc[kid].subjects * self.df_tutors.loc[tutor].subjects 
        s = [f_sub(i) for i in range(len(subjects)) if self.df_students.loc[kid].subjects[i]>0]
        fcs = [int(self.df_students.loc[kid].subjects[i]) for i in range(len(subjects)) if self.df_students.loc[kid].subjects[i]>0]
        ixs= np.argsort(fcs)[::-1]
        return list(np.array(s)[ixs])

    def find_matching_school(self, kid, tutor):
        return ["Vanier", "Camaradiere", "Charlesbourg"][int(np.argwhere(self.df_students.loc[kid].school))]

    def all_possible_dispos(self, kid, tutor, session=0.75):
        k = self.df_students.loc[kid].dispo
        t = self.df_tutors.loc[tutor].dispo
        
        dispos = []
        for key,item in k.items():
            if key in t:
                t1, t2 = t[key]
                t1k, t2k = item
                if min(t2, t2k)-max(t1, t1k)>session:
                    dispos.append(f"{key} - {float2hour(max(t1, t1k))} à {float2hour(min(t2, t2k))}")
        return dispos   

    def explain(self):

        paired_tutors = np.unique([s[1] for s in self.accepted_shifts])
        print(f"Paired tutors: {len(paired_tutors)} / {len(self.df_tutors)}")

        paired_students = np.unique([s[0] for s in self.accepted_shifts])
        print(f"Paired kids: {len(paired_students)} / {len(self.df_students)}")



    def as_dataframe(self):
        results = []
        for pair in self.accepted_shifts:
            kid, tutor = pair
            dispos = self.all_possible_dispos(kid, tutor)
            subjs = self.find_matching_subjects(kid, tutor)
            school = self.find_matching_school(kid, tutor)
            
            kid = self.df_students.loc[kid]
            tutor = self.df_tutors.loc[tutor]
            
            d = {
                "Élève": kid.nom,
                "Tuteur": tutor.nom,
                "Dispos": dispos,
                "École": school,
                "Matières": subjs,
            }
            results.append(d)
        df_results = pd.DataFrame(results)
        return df_results

    def save(self, filename):
        df_results = self.as_dataframe()
        df_results = df_results.sort_values(by=['École'])
        df_results.to_excel(filename)
        