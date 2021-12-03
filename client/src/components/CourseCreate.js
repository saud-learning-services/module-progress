import {
  Create,
  SimpleForm,
  TextInput,
  ArrayInput,
  SimpleFormIterator,
} from "react-admin";

const CourseCreate = (props) => {
  return (
    <Create title="Create a Course" {...props}>
      <SimpleForm>
        <TextInput label="Course ID" source="id" />
        <TextInput label="Course Name" source="course_name" />
        <ArrayInput source="users">
          <SimpleFormIterator>
            <TextInput label="CWL" source="id" />
            <TextInput label="Name" source="name" />
          </SimpleFormIterator>
        </ArrayInput>
      </SimpleForm>
    </Create>
  );
};

export default CourseCreate;
