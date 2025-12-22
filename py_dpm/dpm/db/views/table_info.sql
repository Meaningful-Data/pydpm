CREATE
OR ALTER
VIEW table_info AS
Select TV.Code as table_code,
    TV.TableVID as table_version_id,
    TV.TableID as table_id,
    MV.ModuleVID as module_version_id,
    MV.Code as module_code,
    VV.VariableVID as variable_version_id,
    VV.VariableID as variable_id
from Module M
         inner join ModuleVersion MV
                    on M.ModuleID = MV.ModuleID and MV.EndReleaseID is NULL
inner join ModuleVersionComposition MVC on MV.ModuleVID = MVC.ModuleVID
         inner join TableVersion TV
                    on MVC.TableVID = TV.TableVID and TV.EndReleaseID is NULL
inner join TableVersionCell TVC on TV.TableVID = TVC.TableVID
         inner join VariableVersion VV on TVC.VariableVID = VV.VariableVID and
                                          VV.EndReleaseID is NULL;