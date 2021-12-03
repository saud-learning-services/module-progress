import { Admin, Resource } from "react-admin";
import restProvider from "ra-data-simple-rest";
import CourseList from "./components/CourseList";
import CourseCreate from "./components/CourseCreate";
import CourseEdit from "./components/CourseEdit";

function App() {
  return (
    <Admin dataProvider={restProvider("http://localhost:3000")}>
      <Resource
        name="courses"
        list={CourseList}
        create={CourseCreate}
        edit={CourseEdit}
      />
    </Admin>
  );
}

export default App;
