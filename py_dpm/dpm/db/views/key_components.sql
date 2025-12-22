CREATE OR ALTER VIEW key_components AS
select tv.Code           as table_code,
       ic.Code           as property_code,
       dt.Code           as data_type,
       tv.TableVID       as table_version_id,
       ic.StartReleaseID as start_release_ic,
       ic.EndReleaseID   as end_release_ic,
       mv.StartReleaseID as start_release_mv,
       mv.EndReleaseID   as end_release_mv
from [dbo].TableVersion tv
         inner join [dbo].KeyComposition kc on tv.KeyID = kc.KeyID
         inner join [dbo].VariableVersion vv on vv.VariableVID = kc.VariableVID
         inner join [dbo].Item i on vv.PropertyID = i.ItemID
         inner join [dbo].ItemCategory ic on ic.ItemID = i.ItemID
         inner join [dbo].Property p on vv.PropertyID = p.PropertyID
         left join [dbo].DataType dt on p.DataTypeID = dt.DataTypeID
         inner join [dbo].ModuleVersionComposition mvc on tv.TableVID = mvc.TableVID
         inner join [dbo].ModuleVersion mv on mvc.ModuleVID = mv.ModuleVID;