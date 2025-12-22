CREATE OR ALTER VIEW hierarchy_variables AS
SELECT scv.SubCategoryID as subcategory_id,
       vv.VariableVID    as variable_vid,
       tvc.CellCode      as cell_code,
       mp.Code           as main_property_code,
       cp.Code           as context_property_code,
       i.Code            as item_code,
       mv.StartReleaseID as start_release_id,
       mv.EndReleaseID   as end_release_id
FROM SubCategoryVersion scv
         inner join SubCategoryItem sci
                    on sci.SubCategoryVID = scv.SubCategoryVID
         inner join ContextComposition cc on cc.ItemID = sci.ItemID
         inner join VariableVersion vv on vv.ContextID = cc.ContextID
         inner join TableVersionCell tvc on vv.VariableVID = tvc.VariableVID
         inner join Property p on vv.PropertyID = p.PropertyID
         inner join DataType dt on p.DataTypeID = dt.DataTypeID
         left join ItemCategory mp on mp.ItemID = vv.PropertyID and mp.EndReleaseID is Null
         left join ItemCategory cp on cp.ItemID = cc.PropertyID and cp.EndReleaseID is Null
         left join ItemCategory i on i.ItemID = cc.ItemID and i.EndReleaseID is Null
         inner join TableVersion tv on tv.TableVID = tvc.TableVID
         inner join ModuleVersionComposition mvc on tv.TableVID = mvc.TableVID
         inner join ModuleVersion mv on mvc.ModuleVID = mv.ModuleVID

where dt.Code in ('m', 'i', 'r')
  and tvc.CellCode is not Null
