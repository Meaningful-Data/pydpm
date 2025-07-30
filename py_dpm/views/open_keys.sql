CREATE
OR ALTER
VIEW open_keys AS
select ic.Code           as property_code,
       dt.Code           as data_type,
       ic.StartReleaseID as start_release,
       ic.EndReleaseID   as end_release
from [dbo].KeyComposition kc
         inner join [dbo].VariableVersion vv on vv.VariableVID = kc.VariableVID
         inner join [dbo].Item i on vv.PropertyID = i.ItemID
         inner join [dbo].ItemCategory ic on ic.ItemID = i.ItemID
         inner join [dbo].Property p on vv.PropertyID = p.PropertyID
         left join [dbo].DataType dt on p.DataTypeID = dt.DataTypeID;