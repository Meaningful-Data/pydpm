CREATE OR ALTER VIEW hierarchy_operand_reference_info AS
select distinct o.code         as operation_code,
                on2.NodeID     as operation_node_id,
                orl.CellID     as cell_id,
                or2.VariableID as variable_id
FROM OperandReferenceLocation orl
         inner join OperandReference or2 on orl.OperandReferenceID = or2.OperandReferenceID
         inner join OperationNode on2 on on2.NodeID = or2.NodeID
         inner join OperationVersion ov on ov.OperationVID = on2.OperationVID
         inner join Operation o on o.OperationID = ov.OperationID
WHERE o.[Source] = 'hierarchy';