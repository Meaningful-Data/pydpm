CREATE OR ALTER VIEW hierarchy_preconditions
AS
SELECT ov.Expression as expression,
       o.Code        as operation_code,
       VV.Code       as variable_code
FROM Operation o
         inner join OperationVersion ov on o.OperationID = ov.OperationID
         inner join dbo.OperationNode N on ov.OperationVID = N.OperationVID
         inner join dbo.OperandReference OR2 on N.NodeID = OR2.NodeID
         inner join dbo.Variable V on OR2.VariableID = V.VariableID
         inner join dbo.VariableVersion VV on V.VariableID = VV.VariableID
where o.Code like 'p_%'
  and Expression not like '%or%';