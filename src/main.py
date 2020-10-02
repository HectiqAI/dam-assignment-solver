from utils import *
from model import pair_students, SolutionPrettyfier

import argparse

if __name__ == "__main__":
    """
    Usage example

    python ./main.py -o ./result.xlsx -ns 50 -nt 50

    """
    parser = argparse.ArgumentParser(description='Compute pairings between students and tutors.')

    parser.add_argument('--sf', type=str, 
                        help='Filename to student xlsx file. To be used with the exact DAM format')
    parser.add_argument('--tf', type=str,
                        help='Filename to tutor xlsx file. To be used with the exact DAM format.')
    parser.add_argument('-nt', '--num_tutors', type=int, default=100,
                        help='Number of fake tutors to generate')
    parser.add_argument('-ns', '--num_students', type=int, default=100,
                        help='Number of fake students to generate')
    parser.add_argument('-w', '--weight', type=int, default=1,
                        help='Weight for making the most number of pairing.')
    parser.add_argument('-o', '--output', type=str,
                        help='Filename to tutor xlsx file.')
    args = parser.parse_args()

    # Load tutors
    if args.tf:
        df_tutors_raw = load_tutors_from_excel(args.tf)
        df_tutors = clean_tutors_df(df_tutors_raw)
        df_tutors = sanitize_tutors_df(df_tutors)
    else:
        # Fake students
        data = generate_fake_entries(num=args.num_tutors)
        df_tutors = pd.DataFrame(data)

    # Load students
    if args.sf:
        df_students_raw = load_students_from_excel(args.sf)
        df_students = clean_students_df(df_students_raw)
    else:
        # Fake students
        data = generate_fake_entries(num=args.num_students)
        df_students = pd.DataFrame(data)

    # Solve
    success, solver, shifts = pair_students(df_students, df_tutors, w_paired=args.weight)
    if success:
        
        solution = SolutionPrettyfier(df_students, df_tutors, solver, shifts)
        solution.explain()
        solution.save(args.output)