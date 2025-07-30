CREATE OR ALTER VIEW operations AS
SELECT o.Code            as operation_code,
       ov.StartReleaseID as start_release,
       ov.EndReleaseID   as end_release,
       ov.Expression     as expression,
       ov.OperationVID   as operation_version_id,
       ov.PreconditionOperationVID as precondition_operation_version_id
from Operation o
         inner join OperationVersion ov on o.OperationId = ov.OperationId
where o.Code in (SELECT DISTINCT o.Code
                 from Operation o
                          inner join OperationVersion ov
                                     on o.OperationID = ov.OperationID
                          left join dbo.OperationScope OS
                                    on ov.OperationVID = OS.OperationVID
                 where OS.IsActive = 1)
--          inner join Expression E on ov.OperationVID = E.OperationVID
-- where E.LanguageID = 2;