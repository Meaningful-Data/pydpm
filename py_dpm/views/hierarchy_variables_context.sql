CREATE or ALTER VIEW hierarchy_variables_context as
SELECT distinct vv.VariableVID    as variable_vid,
                cp.Code           as context_property_code,
                i.Code            as item_code,
                mv.StartReleaseID as start_release_id,
                mv.EndReleaseID   as end_release_id
FROM VariableVersion vv
         inner join ContextComposition cc on cc.ContextID = vv.ContextID
         inner join ItemCategory cp on cp.ItemID = cc.PropertyID and cp.EndReleaseID is Null
         inner join ItemCategory i on i.ItemID = cc.ItemID and i.EndReleaseID is Null
         inner join TableVersionCell tvc on vv.VariableVID = tvc.VariableVID
         inner join TableVersion tv on tvc.TableVID = tv.TableVID
         inner join ModuleVersionComposition mvc on tv.TableVID = mvc.TableVID
         inner join ModuleVersion mv on mvc.ModuleVID = mv.ModuleVID;