CREATE
OR ALTER
VIEW data_types AS
SELECT vv.VariableID     as datapoint,
       dt.Code           as data_type,
       vv.StartReleaseID as start_release,
       vv.EndReleaseID   as end_release
from VariableVersion vv
         inner join Property p on
    p.PropertyID = vv.PropertyID
         inner join DataType dt on
    dt.DataTypeID = p.DataTypeID