import argparse
import preprocessing as pr

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load and filter combined dataframe of .tenv files")
    
    parser.add_argument("--gap_tolerance", type=int, default=1000, help="Gap tolerance threshold in days (default: 1000)")
    parser.add_argument("--load_percentage", type=int, default=100, help="Percentage of .tenv files to load (default: 100)")
    parser.add_argument("--target_magnitude", type=float, default=None, help="Minimum earthquake magnitude to filter by")
    parser.add_argument("--eq_count", type=int, default=None, help="Exact number of unique earthquake events required per station")
    parser.add_argument("--save", action="store_true", help="Save the combined dataframe")
    
    args = parser.parse_args()

    parent_path = './geodesy_data'
    pre = pr.Preprocessor(parent_path=parent_path)
    print('Creating geodesy_data/combined_tenv.csv, this may take a while.')
    tenv_df = pre.load_combined_df(gap_tolerance=args.gap_tolerance,
                                   load_percentage=args.load_percentage,
                                   target_magnitude=args.target_magnitude,
                                   eq_count=args.eq_count,
                                   save=args.save)
