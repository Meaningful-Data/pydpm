CREATE OR ALTER VIEW module_from_table AS
SELECT MV.Code      as module_code,
       TV.Code     as table_code,
       MV.FromReferenceDate as from_date,
       MV.ToReferenceDate   as to_date
from Module m
         inner join ModuleVersion MV on m.ModuleID = MV.ModuleID
         inner join ModuleVersionComposition MVC
                    on MV.ModuleVID = MVC.ModuleVID
         inner join TableVersion TV on MVC.TableVID = TV.TableVID
where TV.Code is not null;