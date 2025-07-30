CREATE
OR ALTER
VIEW precondition_info AS
select opN.NodeID as operation_node_id,
       opN.OperationVID as operation_version_id,
       vv.VariableVID as variable_version_id,
        vv.VariableID as variable_id,
        vv.Code as variable_code,
        v.Type as variable_type,
        o.Code as operation_code
from [dbo].OperationNode opN
         left join [dbo].OperandReference opR on opN.NodeID = opR.NodeID
         inner join [dbo].OperationVersion ov on ov.OperationVID = opN.OperationVID
         inner join [dbo].Operation o on o.OperationID = ov.OperationID
         inner join [dbo].VariableVersion vv on vv.VariableVID = opR.VariableID
         inner join [dbo].Variable v on v.VariableID = vv.VariableID
         where v.Type = 'filingIndicator';