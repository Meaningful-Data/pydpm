CREATE OR ALTER VIEW operation_versions_from_module_version AS
SELECT MV.ModuleVID                as module_version_id,
       MV.ModuleID,
       MV.StartReleaseID,
       MV.EndReleaseID,
       MV.Code                     as module_code,
       MV.VersionNumber,
       MV.FromReferenceDate        as from_date,
       MV.ToReferenceDate          as to_date,
       OSC.OperationScopeID        as operation_scope_id,
       OS.IsActive                 as is_active,
       OS.Severity                 as severity,
       OS.FromSubmissionDate,
       ov.OperationVID             as operation_version_id,
       ov.OperationID,
       ov.PreconditionOperationVID as precondition_operation_version_id,
       ov.StartReleaseID           as operation_start_release_id,
       ov.EndReleaseID             as operation_end_release_id,
       ov.Expression               as expression,
       o.Code                      as operation_code,
       o.[Type]                    as operation_type,
       o.[Source]                  as operation_source
from ModuleVersion MV
         inner join OperationScopeComposition OSC
                    on OSC.ModuleVID = MV.ModuleVID
         inner join OperationScope OS
                    on OSC.OperationScopeID = OS.OperationScopeID
         inner join OperationVersion ov on ov.OperationVID = OS.OperationVID
         inner join Operation o on o.OperationID = ov.OperationID
where OS.IsActive = 1;