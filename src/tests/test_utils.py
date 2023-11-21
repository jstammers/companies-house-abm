import pandas as pd
from io import StringIO
from pandas.testing import assert_frame_equal


def test_fill_hierarchy():
    init = """a,b,c,v\na1,,,1\n,b1,,2\n,,c1,3\na2,,,4\n,b2,,5\n,,c2,6"""
    expected = """a,b,c,v
    a1,,,1
    a1,b1,,2
    a1,b1,c1,3
    a2,,,4
    a2,b2,,5
    a2,b2,c2,6
    """
    index_columns = ['a', 'b', 'c']
    df = pd.read_csv(StringIO(init))

    # implement the fill_hierarchy function


    def fill_hierarchy(df, index_columns):
        """
        Fills in missing values in a DataFrame based on a hierarchy of index columns.

        Args:
            df (pandas.DataFrame): The DataFrame to fill in.
            index_columns (list): A list of column names to use as the hierarchy of index columns.

        Returns:
            pandas.DataFrame: The filled-in DataFrame.
        """
        # Forward-fill missing values in each level of the index
        for i in range(len(index_columns)):
            df.iloc[:,i] = df.iloc[:, i].ffill()

        # Reset the index to columns and return the filled-in DataFrame
        return df
    df_filled = fill_hierarchy(df, index_columns)
    df_expected = pd.read_csv(StringIO(expected))
    assert_frame_equal(df_filled, df_expected)

